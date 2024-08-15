import base64
import hashlib
import io
import json
import random
import string
import tarfile
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from gzip import GzipFile
from pathlib import Path, PurePosixPath
from typing import IO, cast

from aiohttp.client_exceptions import ClientResponseError
from docker_registry_client_async import DockerRegistryClientAsync, ImageName
from lightkube import operators as op
from lightkube.config.kubeconfig import KubeConfig
from lightkube.core.exceptions import ApiError
from lightkube.models.core_v1 import (
    Container,
    ContainerPort,
    EnvVar,
    EnvVarSource,
    KeyToPath,
    PodSpec,
    SecretKeySelector,
    SecretVolumeSource,
    Volume,
    VolumeMount,
)
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.batch_v1 import Job
from lightkube.resources.core_v1 import Namespace, Pod, Secret, Service
from lightkube.types import CascadeType
from loguru import logger
from miniopy_async import Minio

from ...config import settings
from ...utils.asc import async_first
from ..compose import Compose
from .client import AsyncClientEx, ImpossibleError, check_meta


class KubeApi:
    _BASE_IP: str = "192.168.1.44"

    BUILD_BUCKET_NAME: str = "dynamic-tasks-build-source"
    BUILD_NAMESPACE: str = "yatb-build"

    RUN_NAMESPACE: str = "yatb-run"  # not used now... :hm"

    client: AsyncClientEx
    s3: Minio
    drca: DockerRegistryClientAsync

    async def init(self) -> None:
        # setup kube
        config = KubeConfig.from_file(settings.kube_config_path) if settings.kube_config_path else None
        self.client = AsyncClientEx(config)  # type: ignore # lib broken

        # setup s3
        self.s3 = Minio(
            endpoint=settings.s3_endpoint,
            access_key=settings.S3_ACCESS,
            secret_key=settings.S3_SECRET,
            secure=False,  # http for False, https for True
        )

        DockerRegistryClientAsync.DEFAULT_PROTOCOL = "http"  # FIXME: tmp
        self.drca = DockerRegistryClientAsync()

        # setup buckets
        await self.setup_s3()

        # setup namespaces
        await self.setup_namespaces()

    async def close(self) -> None:
        await self.client.close()
        await self.drca.close()

    async def setup_namespaces(self) -> None:
        for ns in [self.BUILD_NAMESPACE]:
            logger.info(f"Checking for {ns = } existance")
            try:
                res = await self.client.get(Namespace, ns)
            except ApiError as ex:
                if ex.status.code != 404:  # noqa: PLR2004
                    logger.warning(f"{ex = } {ex.status = }")
                    raise

                logger.info(f"{ns = } not found, creating")
                res = await self.client.create(Namespace(metadata=ObjectMeta(name=ns)))
                logger.info(f"{res = } created")
            else:
                logger.info(f"{ns = } exists")

    async def setup_network(self) -> None:
        # TODO: fix me
        pass

    async def setup_s3(self) -> None:
        if not await self.s3.bucket_exists(self.BUILD_BUCKET_NAME):
            await self.s3.make_bucket(self.BUILD_BUCKET_NAME)

    @classmethod
    def generate_name(cls, alphabet: str = string.digits + string.ascii_lowercase, n: int = 16) -> str:
        return "".join(random.choices(alphabet, k=n))  # noqa: S311

    def get_image_name(self, name: str) -> str:
        return f"{self._BASE_IP}:5000/prebuild-images/{name}:latest"

    def fix_image_name(self, src: str) -> str:
        return src.replace(f"{self._BASE_IP}:5000", "registry.local")

    @asynccontextmanager
    async def docker_config_json_secret(
        self,
        docker_login: str,
        docker_password: str,
        name: str | None = None,
    ) -> AsyncGenerator[Secret, None]:
        name = name or f"dockerconfig-{docker_login}"

        auth = base64.b64encode(f"{docker_login}:{docker_password}".encode()).decode()
        raw_secret = {"auths": {"https://index.docker.io/v1/": {"auth": auth}}}
        encoded_secret = base64.b64encode(json.dumps(raw_secret).encode()).decode()

        async with self.client.ctx(
            Secret(
                metadata=ObjectMeta(
                    name=name,
                    namespace=self.BUILD_NAMESPACE,
                    annotations={
                        "rubikoid.ru/mountVolume-path": "/kaniko/.docker/config.json",
                        "rubikoid.ru/mountVolume-key": ".dockerconfigjson",
                        "rubikoid.ru/mountVolume-ro": "True",
                    },
                ),
                type="kubernetes.io/dockerconfigjson",
                immutable=True,
                data={".dockerconfigjson": encoded_secret},
            ),
        ) as secret:
            yield secret

    async def build(
        self,
        name: str,
        source: Path,
        *,
        destination_override: str | None = None,
        secrets: list[Secret] | None = None,
        dockerfile: Path | str = Path("Dockerfile"),
        skip_build: bool = False,
    ) -> str:
        assert source.is_absolute()
        assert source.is_dir()
        assert (source / dockerfile).exists()

        build_name = name  # self.generate_name()
        raw_img_name = f"{build_name}.tar.gz"

        # some customization
        destination = destination_override or self.get_image_name(build_name)

        if skip_build:
            return destination

        with io.BytesIO() as buff:
            with (
                # have to separately create gzip, because we need to setup mtime=0
                GzipFile(fileobj=buff, mode="wb", mtime=0) as gzip,
                tarfile.open(
                    # https://stackoverflow.com/a/58407810
                    fileobj=cast(IO[bytes], gzip),  # IDK WHY, but for some reason gzip is not IO[bytes]...
                    mode="w|",
                ) as tar,
            ):
                for file in source.iterdir():
                    tar.add(file, arcname=file.relative_to(source))  # string absolute long path
            buff.seek(0)  # reset to 0. because... you knew.

            # calc tar hash and check whenever it already builded
            hash_digest = hashlib.sha256(buff.getbuffer()).hexdigest()

            try:
                tags_resp = await self.drca.get_tags(
                    ImageName.parse(destination),
                )

                if hash_digest in tags_resp.tags["tags"]:
                    logger.info(
                        f"{hash_digest} found in {tags_resp.tags = } for {destination = }, not building this anymore",
                    )
                    return destination
                else:
                    logger.info(
                        f"{hash_digest} not found in {tags_resp.tags = } for {destination = }, so building...",
                    )

            except ClientResponseError as ex:
                if ex.status != 404:
                    raise
                logger.info(f"No image for {destination = } exists so far")

            size = len(buff.getbuffer())
            await self.s3.put_object(
                self.BUILD_BUCKET_NAME,
                raw_img_name,
                buff,
                length=size,
            )

            logger.info(
                f"Uploaded archive from {source} ({size = }) as 's3://{self.BUILD_BUCKET_NAME}/{raw_img_name}'",
            )

        # more customization
        volume_mounts: list[VolumeMount] = []
        volumes: list[Volume] = []
        for secret in secrets or []:
            if not check_meta(secret.metadata) or not secret.metadata.annotations:
                raise ImpossibleError

            volume_name = f"{secret.metadata.name}-volume"
            secret_key = secret.metadata.annotations["rubikoid.ru/mountVolume-key"]
            volumes.append(
                Volume(
                    name=volume_name,
                    secret=SecretVolumeSource(
                        secretName=secret.metadata.name,
                        items=[
                            KeyToPath(
                                secret_key,
                                path=secret_key,
                            )
                        ],
                    ),
                )
            )

            mount_path = secret.metadata.annotations["rubikoid.ru/mountVolume-path"]
            read_only = bool(secret.metadata.annotations.get("rubikoid.ru/mountVolume-ro", "True"))
            volume_mounts.append(
                VolumeMount(
                    name=volume_name,
                    mountPath=mount_path,
                    readOnly=read_only,
                    subPath=secret_key,
                ),
            )

        _kaniko = self.client.simple_job(
            f"kaniko-build-{build_name}",
            namespace=self.BUILD_NAMESPACE,
            pod_spec=PodSpec(
                containers=[
                    Container(
                        name="kaniko",
                        # image="rubikoid/yatb-k8s-builder-base:base",  # "gcr.io/kaniko-project/executor:v1.23.2",
                        image="gcr.io/kaniko-project/executor:v1.23.2",
                        args=[
                            f"--dockerfile={PurePosixPath('/kaniko/buildcontext') / dockerfile}",
                            f"--context=s3://{self.BUILD_BUCKET_NAME}/{raw_img_name}",
                            f"--destination={destination}",
                            "--cache=true",
                            "--cache-run-layers=true",
                            "--cache-copy-layers=true",
                            f"--cache-repo={self._BASE_IP}:5000/cache",
                        ],
                        # args=[
                        #     "-c",
                        #     """
                        #     env;
                        #     ls -la /kaniko/.docker;
                        #     ls -la /kaniko/.docker/config.json;
                        #     cat /kaniko/.docker/config.json;
                        #     """.strip(),
                        # ],
                        env=[
                            EnvVar(
                                "S3_ENDPOINT",
                                value=f"http://{self._BASE_IP}:{settings.S3_PORT}",
                            ),
                            # need to specify this to use path-stye minio,
                            # and don't try to resolve http://bucket.ip:port/file
                            EnvVar("S3_FORCE_PATH_STYLE", "true"),
                            # i have AWS. Don't work without this
                            EnvVar("AWS_REGION", "us-east-1"),  # i have AWS
                            EnvVar("AWS_ACCESS_KEY_ID", settings.S3_ACCESS),
                            EnvVar("AWS_SECRET_ACCESS_KEY", settings.S3_SECRET),
                        ],
                        volumeMounts=volume_mounts,
                    ),
                ],
                volumes=volumes,
                restartPolicy="Never",
            ),
        )

        async with self.client.ctx(_kaniko, cascade=CascadeType.FOREGROUND) as kaniko:
            if not check_meta(kaniko.metadata):
                raise ImpossibleError

            logger.info("Wait for job ready")
            await self.client.wait_ex(
                Job,
                kaniko.metadata.name,
                namespace=kaniko.metadata.namespace,
                cb=lambda x: x.get("ready", 0) == 1,
            )

            kaniko_pod = await async_first(
                self.client.list(
                    Pod,
                    labels={"app.kubernetes.io/name": op.equal(kaniko.metadata.name)},
                    namespace=kaniko.metadata.namespace,
                ),
            )

            if not check_meta(kaniko_pod.metadata):
                raise ImpossibleError

            logger.info("Waiting for kaniko pod be ready")

            kaniko_pod = await self.client.wait(
                Pod,
                kaniko_pod.metadata.name,
                for_conditions=["PodReadyToStartContainers"],
                namespace=kaniko.metadata.namespace,
            )

            if not check_meta(kaniko_pod.metadata):
                raise ImpossibleError

            logger.info(
                f"Kaniko pod created: '{kaniko_pod.metadata.namespace}.{kaniko_pod.metadata.name}'",
            )

            async for line in self.client.log(
                kaniko_pod.metadata.name,
                namespace=kaniko_pod.metadata.namespace,
                follow=True,
                newlines=False,
            ):
                logger.trace(f"Building {name!r}: {line}")

        logger.info(f"{name!r} builded as {destination!r}")

        # upload special caching tag
        img_name = ImageName.parse(destination)
        manifest = await self.drca.get_manifest(img_name)
        patched_img = img_name.clone().set_tag(hash_digest)
        await self.drca.put_manifest(patched_img, manifest.manifest)

        return destination

    async def oneshot(self, name: str) -> None:
        image = self.get_image_name(name)
        raise NotImplementedError

    @asynccontextmanager
    async def run_in_ns(self, name: str) -> AsyncGenerator[tuple[str, Namespace], None]:
        run_prefix = self.generate_name()
        res = await self.client.create(
            Namespace(
                metadata=ObjectMeta(
                    name=f"{name}-{run_prefix}",
                )
            )
        )

        if not res.metadata or not res.metadata.name:
            raise ImpossibleError(f"{res = }")

        try:
            await self.setup_ns(res)
            yield res.metadata.name, res
        finally:
            await self.client.delete(
                Namespace,
                name=res.metadata.name,
                grace_period=0,
                cascade=CascadeType.FOREGROUND,
            )
            logger.info(f"Cleaned namespace '{res.metadata.name}'")

    async def setup_ns(self, ns: Namespace) -> None:
        if not ns.metadata or not ns.metadata.name:
            raise ImpossibleError(f"{ns = }")

        pass

    async def service(
        self,
        name: str,
        compose: Compose,
        flag: str,
        host: str,
        port: int,
        *,
        skip_build: bool = False,
    ) -> AsyncExitStack:
        # images: dict[str, str] = {}
        containers: dict[str, Container] = {}
        # build stage
        for svc_name, svc in compose.services.items():
            if not svc.build:
                if not svc.image:
                    raise Exception("no")
                image = svc.image
            elif isinstance(svc.build, Path):
                # TODO: do not build on every run
                image = await self.build(f"{name}-{svc_name}", svc.build, skip_build=skip_build)
            else:
                image = await self.build(
                    f"{name}-{svc_name}",
                    svc.build.context,
                    dockerfile=svc.build.dockerfile,
                    skip_build=skip_build,
                )

            image = self.fix_image_name(image)

            containers[svc_name] = Container(
                name=svc_name,
                image=image,
                command=svc.prepared_command,
                ports=[ContainerPort(port.internal_port) for port in svc.ports],
                # env=[],
            )

        def patch_container(container: Container, secret: Secret, key: str) -> Container:
            if not check_meta(secret.metadata):
                raise ImpossibleError

            if container.env is None:
                container.env = []
            container.env.append(
                EnvVar(
                    name=key,
                    valueFrom=EnvVarSource(
                        secretKeyRef=SecretKeySelector(
                            name=secret.metadata.name,
                            key=key,
                        ),
                    ),
                ),
            )

            return container

        stack = AsyncExitStack()
        ns_name, ns = await stack.enter_async_context(self.run_in_ns(f"{name}"))
        flag_secret = await stack.enter_async_context(
            self.client.ctx(
                Secret(
                    metadata=ObjectMeta(
                        name=f"{name}-flag",
                        namespace=ns_name,
                    ),
                    immutable=True,
                    stringData={"FLAG": flag},
                ),
            )
        )

        # run stage
        services: list[Service] = []

        for svc_name, container in containers.items():
            patch_container(container, flag_secret, "FLAG")

            if container.ports:
                container_port = container.ports[0]  # TODO: handle multiple ports...
                service = self.client.ctx(
                    self.client.simple_service(
                        svc_name,
                        ns_name,
                        port,
                        container_port.containerPort,
                        [host],
                    ),
                )
                service = await stack.enter_async_context(service)
                services.append(service)

            deployment = self.client.ctx(
                self.client.simple_deployment(
                    svc_name,
                    ns_name,
                    PodSpec(containers=[container]),
                ),
            )
            await stack.enter_async_context(deployment)

        for service in services:
            if not service.spec or not service.spec.externalIPs or not service.spec.ports:
                raise ImpossibleError

            # logger.info(f"{service = }")

            addr = f"http://{service.spec.externalIPs[0]}:{service.spec.ports[0].port}"

            logger.info(
                f"Started at {service.spec.externalIPs} -> {[i.port for i in service.spec.ports]}; "
                f"{addr = }; "  # ...
                f"{service.spec.clusterIPs = }",
            )

        return stack

    async def test(self):
        logger.info("Simple cluster status:")
        async for ns in self.client.list(Namespace):
            if not ns.metadata or not ns.metadata.name:
                logger.warning(f"{ns = } no metadata or name")
                continue

            logger.info(f"Found ns: {ns.metadata.name}")

        async for pod in self.client.list(Pod, namespace="*"):
            if not pod.metadata or not pod.status:
                logger.warning(f"{pod = } no metadata / status")
                continue

            logger.info(f"{pod.metadata.namespace}.{pod.metadata.name}: {pod.status.podIPs}")
