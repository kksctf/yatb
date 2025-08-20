import base64
import json
import random
import string
from collections.abc import AsyncGenerator, Mapping, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path, PurePosixPath

from aiohttp.client_exceptions import ClientResponseError
from docker_registry_client_async import DockerRegistryClientAsync, ImageName
from lightkube.config.kubeconfig import KubeConfig
from lightkube.core.exceptions import ApiError
from lightkube.models.core_v1 import (
    Capabilities,
    Container,
    ContainerPort,
    EnvVar,
    EnvVarSource,
    KeyToPath,
    PersistentVolumeClaimVolumeSource,
    PodSecurityContext,
    PodSpec,
    SecretKeySelector,
    SecretVolumeSource,
    SecurityContext,
    Sysctl,
    Volume,
    VolumeMount,
)
from lightkube.models.core_v1 import ResourceRequirements as kResourceRequirements
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.apps_v1 import Deployment
from lightkube.resources.core_v1 import Namespace, PersistentVolumeClaim, Pod, Secret, Service
from lightkube.types import CascadeType
from loguru import logger
from miniopy_async.datatypes import Object

from yatb.shared.dtc.models.vpn import UserNetInfo
from yatb.shared.s3.client import MinioEx

from ...config import settings
from ...controllers.ports_controller import PortsEnv
from ..compose import Compose
from .client import AsyncClientEx, ImpossibleError, check_meta

# fixme: two builds at one time

_base_path = Path(__file__).parent


class KubeApi:
    BUILD_NAMESPACE: str = "yatb-build"

    RUN_NAMESPACE: str = "yatb-run"  # not used now... :hm"

    client: AsyncClientEx
    s3: MinioEx
    drca: DockerRegistryClientAsync

    gradle_cache_name: str = "gradle-cache"
    gradle_cache_pvc: PersistentVolumeClaim

    async def init(self) -> None:
        # setup kube
        config = KubeConfig.from_file(settings.kube_config_path) if settings.kube_config_path else None
        self.client = AsyncClientEx(config, field_manager="dtc")

        # setup s3
        self.s3 = MinioEx(
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

        logger.info("KubeAPI init ok")

    async def close(self) -> None:
        # logger.critical(f"Closing KubeApi")
        # await self.client.close()
        # logger.critical(f"Closed KubeApi, closing drca")
        await self.drca.close()
        # logger.critical(f"Closed drca")

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

        try:
            self.gradle_cache_pvc = await self.client.find_volume(self.gradle_cache_name, self.BUILD_NAMESPACE)
        except Exception as ex:
            logger.warning(f"GradleCachePVC Not found: {ex!r}, creating")
            self.gradle_cache_pvc = await self.client.create(
                self.client.simple_volume(
                    self.gradle_cache_name,
                    self.BUILD_NAMESPACE,
                    size="10Gi",
                ),
            )

            if not check_meta(self.gradle_cache_pvc.metadata):
                raise ImpossibleError from ex

    async def setup_network(self) -> None:
        # TODO: fix me
        pass

    async def setup_s3(self) -> None:
        await self.s3.setup_buckets(
            [
                settings.STATIC_BUCKET_NAME,
                settings.TASKS_BUCKET_NAME,
                settings.BUILD_RESULT_BUCKET_NAME,
            ],
        )

    @classmethod
    def generate_name(cls, alphabet: str = string.digits + string.ascii_lowercase, n: int = 16) -> str:
        return "".join(random.choices(alphabet, k=n))  # noqa: S311

    def get_image_name(self, name: str) -> str:
        return f"{settings.DOCKER_REGISTRY_HOST}:{settings.DOCKER_REGISTRY_PORT}/prebuild-images/{name}:latest"

    def fix_image_name(self, src: str) -> str:
        return src.replace(f"{settings.DOCKER_REGISTRY_HOST}:{settings.DOCKER_REGISTRY_PORT}", "registry.local")

    @asynccontextmanager
    async def docker_config_json_secret(
        self,
        docker_login: str,
        docker_password: str,
        name: str | None = None,
    ) -> AsyncGenerator[Secret, None]:
        name = name or f"dockerconfig-{docker_login}"

        auth = base64.b64encode(f"{docker_login}:{docker_password}".encode()).decode()
        raw_secret = {"auths": {f"{settings.EXTERNAL_DOCKER_REGISTRY}": {"auth": auth}}}
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
        kaniko_args: Sequence[str] = [],
    ) -> str:
        assert source.is_absolute()
        assert source.is_dir()
        assert (source / dockerfile).exists()

        build_name = name  # self.generate_name()

        # some customization
        destination = destination_override or self.get_image_name(build_name)

        # if isinstance(source, Path):
        raw_img_name = f"generic_{build_name}.tar.gz"
        hash_digest = await self.s3.upload_directory(
            source,
            settings.TASKS_BUCKET_NAME,
            raw_img_name,
        )
        # else:
        #     raw_img_name, hash_digest = source

        try:
            parsed = ImageName.parse(destination)
            if settings.DOCKER_REGISTRY_HOST_LOCAL:
                parsed.endpoint = f"{settings.DOCKER_REGISTRY_HOST_LOCAL}:{settings.DOCKER_REGISTRY_PORT_LOCAL}"
            # logger.warning(f"{parsed.digest = }")
            # logger.warning(f"{parsed.endpoint = }")
            # logger.warning(f"{parsed.image = }")
            # logger.warning(f"{parsed.tag = }")
            tags_resp = await self.drca.get_tags(parsed)

            if hash_digest in tags_resp.tags["tags"]:
                logger.info(
                    f"{hash_digest} found in {tags_resp.tags = } for {destination = }, not building this anymore",
                )
                return destination

            logger.info(
                f"{hash_digest} not found in {tags_resp.tags = } for {destination = }, so building...",
            )

        except ClientResponseError as ex:
            if ex.status != 404:
                raise
            logger.info(f"No image for {destination = } exists so far")

        if skip_build:
            return destination

        # __ihatedocker = self.docker_config_json_secret(_DOCKER_LOGIN, _DOCKER_PW)
        # __ihatedocker_secret = await __ihatedocker.__aenter__()

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
                        args=(
                            [  # noqa: RUF005
                                f"--dockerfile={PurePosixPath('/kaniko/buildcontext') / dockerfile}",
                                f"--context=s3://{settings.TASKS_BUCKET_NAME}/{raw_img_name}",
                                f"--destination={destination}",
                                "--cache=true",
                                "--cache-run-layers=true",
                                "--cache-copy-layers=true",
                                f"--cache-repo={settings.DOCKER_REGISTRY_HOST}:{settings.DOCKER_REGISTRY_PORT}/cache",
                                "--insecure",
                                f"--insecure-registry={settings.DOCKER_REGISTRY_HOST}:{settings.DOCKER_REGISTRY_PORT}",
                                f"--insecure-registry={settings.DOCKER_REGISTRY_HOST}",
                                # f"--registry-map",
                            ]
                            + list(kaniko_args)
                        ),
                        # image="alpine:3.21",
                        # command=["/bin/sh"],
                        # args=[
                        #     "-c",
                        #     """
                        #     env;
                        #     ls -la /kaniko/.docker;
                        #     ls -la /kaniko/.docker/config.json;
                        #     cat /kaniko/.docker/config.json;
                        #     ping 1.1.1.1 -c 4
                        #     ping google.com -c 4
                        #     """.strip(),
                        # ],
                        #
                        env=[
                            # EnvVar(
                            #     "KANIKO_REGISTRY_MAP",
                            #     "registry.local=http://{settings.DOCKER_REGISTRY_HOST}:5000",
                            # ),
                            EnvVar(
                                "S3_ENDPOINT",
                                value=f"http://{settings.S3_HOST_KANIKO}:{settings.S3_PORT_KANIKO}",
                            ),
                            # need to specify this to use path-stye minio,
                            # and don't try to resolve http://bucket.ip:port/file
                            EnvVar("S3_FORCE_PATH_STYLE", "true"),
                            # i have AWS. Don't work without this
                            EnvVar("AWS_REGION", "us-east-1"),  # i hate AWS
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

        # FIXME: тут иногда вылетает исключение, если пытаться одновременно сбилдить один и тот же таск двум людям
        # надо повесить лочку
        async with self.client.ctx(_kaniko, cascade=CascadeType.FOREGROUND) as kaniko:
            await self.client.wait_for_job_ready_with_logs(kaniko)

        logger.info(f"{name!r} builded as {destination!r}")

        # upload special caching tag
        img_name = ImageName.parse(destination)
        if settings.DOCKER_REGISTRY_HOST_LOCAL:
            img_name.endpoint = f"{settings.DOCKER_REGISTRY_HOST_LOCAL}:{settings.DOCKER_REGISTRY_PORT_LOCAL}"
        manifest = await self.drca.get_manifest(img_name)

        patched_img = img_name.clone().set_tag(hash_digest)
        if settings.DOCKER_REGISTRY_HOST_LOCAL:
            patched_img.endpoint = f"{settings.DOCKER_REGISTRY_HOST_LOCAL}:{settings.DOCKER_REGISTRY_PORT_LOCAL}"
        await self.drca.put_manifest(patched_img, manifest.manifest)

        return destination

    @asynccontextmanager
    async def run_in_ns(
        self,
        name: str,
        *,
        prefix: str | None = None,
        annotations: Mapping[str, str] = {},
    ) -> AsyncGenerator[tuple[str, Namespace], None]:
        prefix = prefix or self.generate_name()
        res = await self.client.create(
            Namespace(
                metadata=ObjectMeta(
                    name=f"{name}-{prefix}",
                    annotations=dict(annotations),
                ),
            ),
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

        # TODO: NS network restrictions

    async def service(
        self,
        name: str,
        ns: Namespace,
        ns_name: str,
        compose: Compose,
        flag: str,
        *,
        # ip_in_cluster: str | None = None,
        stack: AsyncExitStack,
        ports_env: PortsEnv,
        skip_build: bool = False,
        extra_env: Mapping[str, str] = {},
        # extra_route: tuple[str, str] | None = None,
    ) -> Namespace:
        # images: dict[str, str] = {}
        containers: dict[str, Container] = {}

        # build stage
        for svc_name, svc in compose.services.items():
            # if it is a VM description: just go away
            if svc.vm:
                continue

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

            # TODO: eww
            image = self.fix_image_name(image)

            env: list[EnvVar] = []
            for env_key, env_value in list(svc.parsed_env.items()) + list(extra_env.items()):
                if env_key == "FLAG":  # WTF: monkeypatch or production ready?????
                    continue

                env.append(
                    EnvVar(
                        name=env_key,
                        value=env_value,
                    ),
                )

            logger.trace(f"Creating container for {svc_name = } with {env = }")

            # create container descriptor thing
            containers[svc_name] = Container(
                name=svc_name,
                image=image,
                args=svc.prepared_command,
                ports=[ContainerPort(port.internal_port) for port in svc.ports]
                + [ContainerPort(port) for port in svc.expose],
                env=env,
                resources=kResourceRequirements(
                    requests=svc.resource.requests.model_dump(),
                    limits=svc.resource.limits.model_dump(),
                ),
            )

        # define function for container patching
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
            ),
        )

        # run stage
        services: list[Service] = []

        for svc_name, container in containers.items():
            svc = compose.services[svc_name]
            if svc.vm:  # don't do this on VMs... for now?
                continue

            patch_container(container, flag_secret, "FLAG")

            # TODO: instead of creating thousands of services, make one service with multiple
            # ServicePort

            for exposing_port in svc.expose:
                service = self.client.ctx(
                    self.client.simple_internal_service(
                        svc_name,
                        ns_name,
                        exposing_port,
                    ),
                )
                service = await stack.enter_async_context(service)
                services.append(service)

            for port in svc.ports:
                public_hp = await ports_env.get_port()
                service = self.client.ctx(
                    self.client.simple_service(
                        svc_name,
                        ns_name,
                        public_hp.port,
                        port.internal_port,
                        settings.EXTERNAL_TO_INTERNAL_IPS_MAPPING[public_hp.host],
                        name_suffix="-public",
                    ),
                )
                service = await stack.enter_async_context(service)
                services.append(service)

            deployment = self.client.ctx(
                self.client.simple_deployment(
                    svc_name,
                    ns_name,
                    PodSpec(
                        containers=[container],
                    ),
                ),
            )
            await stack.enter_async_context(deployment)

        for service in services:
            if not service.spec or not service.spec.ports:
                raise ImpossibleError

            if not service.spec.externalIPs:
                logger.info(f"Service without externalIPs {service.spec = } (99% this is ok)")
                continue

            # logger.info(f"{service = }")

            addr = f"http://{service.spec.externalIPs[0]}:{service.spec.ports[0].port}"

            logger.info(
                f"Started at {service.spec.externalIPs} -> {[i.port for i in service.spec.ports]}; "
                f"{addr = }; "  # ...
                f"{service.spec.clusterIPs = }",
            )

        return ns

    async def oneshot(
        self,
        name: str,
        source: Path,
        env: dict[str, str],
        s3_prefix: str,
        *,
        resources: kResourceRequirements = kResourceRequirements(
            requests={
                "cpu": "1000m",
                "memory": "512Mi",
            },
            limits={
                "cpu": "3000m",
                "memory": "3Gi",
            },
        ),
    ) -> str:
        _EXPORT_PATH = "/build"

        objects: list[Object] = await self.s3.list_objects(  # noqa: SLF001
            settings.BUILD_RESULT_BUCKET_NAME,
            s3_prefix,
            recursive=True,
        )._collect_objects()

        logger.trace(f"For {s3_prefix = } found {objects = }")

        if len(objects) > 0:
            return objects[0].object_name

        image = await self.build(
            name,
            source=source,
        )

        uploader_image = await self.build(
            "uploader",
            source=_base_path.parent.parent / "extra",
        )

        # suffix = "kaqtk3fybk6exc4j"
        suffix = self.generate_name()
        stack = AsyncExitStack()
        async with stack:
            # export_volume = await self.client.create(
            #     self.client.simple_volume(
            #         name=f"{name}-{suffix}",
            #         namespace=self.BUILD_NAMESPACE,
            #         size="128Mi",
            #     ),
            # )
            export_volume = await stack.enter_async_context(
                self.client.ctx(
                    self.client.simple_volume(
                        name=f"{name}-{suffix}",
                        namespace=self.BUILD_NAMESPACE,
                        size="128Mi",
                    ),
                ),
            )
            # export_volume = await self.client.find_volume(
            #     name=f"{name}-{suffix}",
            #     namespace=self.BUILD_NAMESPACE,
            # )

            if not check_meta(export_volume.metadata):
                raise ImpossibleError

            logger.trace(f"{export_volume = }")

            volumes = [
                Volume(
                    name="build-volume",
                    persistentVolumeClaim=PersistentVolumeClaimVolumeSource(
                        claimName=export_volume.metadata.name,
                    ),
                ),
                Volume(
                    name="gradle-cache",
                    persistentVolumeClaim=PersistentVolumeClaimVolumeSource(
                        claimName=self.gradle_cache_name,
                    ),
                ),
            ]
            volume_mounts = [
                VolumeMount(
                    name="build-volume",
                    mountPath=_EXPORT_PATH,
                ),
                VolumeMount(
                    name="gradle-cache",
                    mountPath="/root/.gradle",
                ),
            ]

            _builder = self.client.simple_job(
                name=f"builder-{name}-{suffix}",
                namespace=self.BUILD_NAMESPACE,
                pod_spec=PodSpec(
                    containers=[
                        Container(
                            name="builder",
                            image=self.fix_image_name(image),
                            env=[
                                EnvVar(
                                    "EXPORT_PATH",
                                    _EXPORT_PATH,
                                ),
                            ]
                            + [EnvVar(i, v) for i, v in env.items()],
                            volumeMounts=volume_mounts,
                            resources=resources,
                        ),
                    ],
                    volumes=volumes,
                    restartPolicy="Never",
                ),
            )

            async with self.client.ctx(_builder, cascade=CascadeType.FOREGROUND):
                await self.client.wait_for_job_ready_with_logs(_builder)
                # input("...?")

            _uploader = self.client.simple_job(
                name=f"uploader-{name}-{suffix}",
                namespace=self.BUILD_NAMESPACE,
                pod_spec=PodSpec(
                    containers=[
                        Container(
                            name="uploader",
                            image=self.fix_image_name(uploader_image),
                            args=[
                                "upload",
                                s3_prefix,
                            ],
                            env=[
                                EnvVar(
                                    "EXPORT_PATH",
                                    _EXPORT_PATH,
                                ),
                            ]
                            + [EnvVar(i, v) for i, v in env.items()]
                            + [
                                EnvVar(
                                    "BUILD_RESULT_BUCKET_NAME",
                                    settings.BUILD_RESULT_BUCKET_NAME,
                                ),
                                EnvVar(
                                    "S3_HOST",
                                    settings.S3_HOST_KANIKO,
                                ),
                                EnvVar(
                                    "S3_PORT",
                                    f"{settings.S3_PORT}",
                                ),
                                EnvVar(
                                    "S3_ACCESS",
                                    settings.S3_ACCESS,
                                ),
                                EnvVar(
                                    "S3_SECRET",
                                    settings.S3_SECRET,
                                ),
                            ],
                            volumeMounts=volume_mounts,
                        ),
                    ],
                    volumes=volumes,
                    restartPolicy="Never",
                ),
            )

            async with self.client.ctx(_uploader, cascade=CascadeType.FOREGROUND):
                await self.client.wait_for_job_ready_with_logs(_uploader)
                # input("...?")

                job_pod = await self.client.find_pod(_uploader)
                if not check_meta(job_pod.metadata):
                    raise ImpossibleError

                async for log in self.client.log(
                    job_pod.metadata.name,
                    namespace=job_pod.metadata.namespace,
                    newlines=False,
                ):
                    if log.endswith("uploaded"):
                        frm = log.index("'")
                        to = log.index("'", frm + 1)
                        parsed_log = log[frm + 1 : to]

                        logger.info(f"{log = } -> {parsed_log = }, {frm = }, {to = }")
                        break  # TODO: make this better
                else:
                    raise Exception("error building shit")

        return f"{parsed_log}"

    async def openvpn(
        self,
        ns: Namespace,
        usernet: UserNetInfo,
        static_key: str,
        *,
        internal_port: int = 11337,
        external_ips: list[str],
        stack: AsyncExitStack,
    ) -> tuple[Deployment, Service]:
        raise Exception

        if not ns.metadata or not ns.metadata.name:
            raise Exception

        ns_name = ns.metadata.name

        # route 10.20.0.0 255.255.0.0 10.10.1.14
        # allow-compression yes
        cfg = f"""
            dev tap0
            proto udp6
            port {internal_port}

            ifconfig {usernet.vpn_server_ip.compressed} {usernet.vpn_net.netmask.compressed}
            route {usernet.client_ip.compressed} 255.255.255.255 {usernet.vpn_client_ip.compressed}

            cipher AES-256-CBC
            auth-nocache

            comp-lzo
            keepalive 10 60
            ping-timer-rem
            persist-key

            <secret>
            {static_key}
            </secret>
        """.strip().replace(
            "            ",
            "",
        )

        ovpn_config = await stack.enter_async_context(
            self.client.ctx(
                Secret(
                    metadata=ObjectMeta(
                        name="openvpn-config",
                        namespace=ns_name,
                    ),
                    immutable=True,
                    data={"server.conf": base64.b64encode(cfg.encode()).decode()},
                ),
            ),
        )

        if not check_meta(ovpn_config.metadata):
            raise Exception

        ovpn = self.client.simple_deployment(
            "openvpn",
            namespace=ns_name,
            extra_pod_meta={
                "annotations": {
                    "cni.projectcalico.org/ipAddrs": f'["{usernet.task_net_vpn.compressed}"]',
                },
            },
            pod_spec=PodSpec(
                containers=[
                    Container(
                        name="openvpn",
                        image="ghcr.io/rubikoid/yatb-k8s-openvpn:latest",
                        command=["/bin/sh", "-c"],
                        args=[
                            "chmod +x /fw.sh && openvpn --config /etc/openvpn/server.conf --script-security 2 --up /fw.sh"
                        ],
                        stdin=True,
                        tty=True,
                        securityContext=SecurityContext(
                            privileged=True,
                            capabilities=Capabilities(add=["NET_ADMIN"]),
                        ),
                        # env=[
                        #     EnvVar(name="CLIENT_IP", value=f"{usernet.client_ip.compressed}"),
                        #     EnvVar(name="SELF_IP", value=f"{usernet.task_net_vpn.compressed}"),
                        # ],
                        ports=[ContainerPort(containerPort=internal_port, protocol="UDP")],
                        volumeMounts=[
                            VolumeMount(
                                name="config",
                                mountPath="/etc/openvpn",
                                readOnly=True,
                            ),
                        ],
                    ),
                ],
                securityContext=PodSecurityContext(sysctls=[Sysctl(name="net.ipv4.ip_forward", value="1")]),
                volumes=[Volume(name="config", secret=SecretVolumeSource(secretName=ovpn_config.metadata.name))],
            ),
        )
        ovpn = await stack.enter_async_context(self.client.ctx(ovpn))

        svc = self.client.simple_service(
            "openvpn",
            namespace=ns_name,
            external_port=usernet.vpn_internal_port,
            target_port=internal_port,
            external_ips=external_ips,
            protocol="UDP",
        )
        svc = await stack.enter_async_context(self.client.ctx(svc))

        return ovpn, svc

    async def openvpn_back(
        self,
        ns: Namespace,
        static_key: str,
        external_port: int,
        *,
        stack: AsyncExitStack,
    ) -> Deployment:
        raise Exception

        if not ns.metadata or not ns.metadata.name:
            raise Exception

        ns_name = ns.metadata.name

        # route 10.20.0.0 255.255.0.0 10.10.1.14
        # allow-compression yes
        cfg = f"""
            dev tap0
            proto udp6
            port {external_port}

            ifconfig 10.240.0.1 255.255.255.0
            route 10.10.0.0 255.255.0.0 10.240.0.2

            cipher AES-256-CBC
            auth-nocache

            comp-lzo
            keepalive 10 60
            ping-timer-rem
            persist-key

            <secret>
            {static_key}
            </secret>
        """.strip().replace(
            "            ",
            "",
        )

        fw = f"""#!/usr/bin/env sh
iptables -t nat -A POSTROUTING -o tap0 -j MASQUERADE
        """

        ovpn_config = await stack.enter_async_context(
            self.client.ctx(
                Secret(
                    metadata=ObjectMeta(
                        name="openvpn-config",
                        namespace=ns_name,
                    ),
                    immutable=True,
                    data={
                        "server.conf": base64.b64encode(cfg.encode()).decode(),
                        "fw.sh": base64.b64encode(cfg.encode()).decode(),
                    },
                ),
            ),
        )

        if not check_meta(ovpn_config.metadata):
            raise Exception

        ovpn = self.client.simple_deployment(
            "openvpn",
            namespace=ns_name,
            pod_spec=PodSpec(
                hostNetwork=True,
                containers=[
                    Container(
                        name="openvpn",
                        image="ghcr.io/rubikoid/yatb-k8s-openvpn:latest",
                        command=["/bin/sh", "-c"],
                        args=["openvpn --config /etc/openvpn/server.conf"],
                        stdin=True,
                        tty=True,
                        securityContext=SecurityContext(
                            privileged=True,
                            capabilities=Capabilities(add=["NET_ADMIN"]),
                        ),
                        volumeMounts=[
                            VolumeMount(
                                name="config",
                                mountPath="/etc/openvpn",
                                readOnly=True,
                            ),
                        ],
                    ),
                ],
                volumes=[Volume(name="config", secret=SecretVolumeSource(secretName=ovpn_config.metadata.name))],
            ),
        )
        ovpn = await stack.enter_async_context(self.client.ctx(ovpn))

        return ovpn

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
