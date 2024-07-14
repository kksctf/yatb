#
import asyncio
from pathlib import Path
import random
import string
import tarfile
import io

from lightkube.config.kubeconfig import KubeConfig
from lightkube.core.async_client import AsyncClient
from lightkube.resources.core_v1 import Namespace, Pod
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.models.core_v1 import PodSpec, Container, EnvVar
from loguru import logger
from miniopy_async import Minio

from ..config import settings
from . import BaseConnector, DynamicTaskInfo


class ImpossibleError(Exception):
    pass


# class WTF:
#     api: kr8sa.Api

#     async def init(self) -> None:
#         self.api = await kr8sa.api(kubeconfig=settings.kube_config_path)

#     async def test(self) -> None:
#         logger.info(f"{await self.api.whoami() = }")
#         logger.info("Listing pods with their IPs:")
#         ret = await self.api.get("pods", namespace=kr8s.ALL)
#         if not isinstance(ret, list):
#             raise Exception("wtf")

#         for i in ret:
#             logger.info(f"{i}")


class KubeApi:
    BUILD_BUCKET_NAME: str = "dynamic-tasks-build-source"
    # BUILD_NAMESPACE: str = "yatb-build-namespace"
    BUILD_NAMESPACE: str = "default"

    client: AsyncClient
    s3: Minio

    async def init(self) -> None:
        # setup kube
        config = KubeConfig.from_file(settings.kube_config_path) if settings.kube_config_path else None
        self.client = AsyncClient(config)  # type: ignore # lib broken

        # setup s3
        self.s3 = Minio(
            endpoint=settings.s3_endpoint,
            access_key=settings.S3_ACCESS,
            secret_key=settings.S3_SECRET,
            secure=False,  # http for False, https for True
        )

        # setup buckets
        await self.setup_s3()

    async def close(self) -> None:
        await self.client.close()

    async def setup_s3(self) -> None:
        if not await self.s3.bucket_exists(self.BUILD_BUCKET_NAME):
            await self.s3.make_bucket(self.BUILD_BUCKET_NAME)

    @classmethod
    def generate_name(cls, alphabet: str = string.digits + string.ascii_lowercase, n: int = 16) -> str:
        return "".join(random.choices(alphabet, k=n))  # noqa: S311

    async def build(self, source: Path, *, _base_ip: str = "10.42.0.1") -> None:
        assert source.is_absolute()
        assert source.is_dir()
        assert (source / "Dockerfile").exists()

        build_name = self.generate_name()
        build_name = "y4fchuw25jbrh0fz"
        raw_img_name = f"{build_name}.tar.gz"

        with io.BytesIO() as buff:
            with tarfile.open(fileobj=buff, mode="w:gz") as tar:
                for file in source.iterdir():
                    tar.add(file, arcname=file.relative_to(source))  # string absolute long path
            buff.seek(0)  # reset to 0. because... you knew.

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

        kaniko = await self.client.create(
            Pod(
                metadata=ObjectMeta(name=f"kaniko-build-{build_name}", namespace=self.BUILD_NAMESPACE),
                spec=PodSpec(
                    containers=[
                        Container(
                            name="kaniko",
                            image="gcr.io/kaniko-project/executor:v1.23.2",
                            args=[
                                "--dockerfile=/kaniko/buildcontext/Dockerfile",
                                f"--context=s3://{self.BUILD_BUCKET_NAME}/{raw_img_name}",
                                f"--destination={_base_ip}:5000/prebuild-images/{build_name}:latest",
                                "--cache=true",
                                "--cache-run-layers=true",
                                "--cache-copy-layers=true",
                                f"--cache-repo={_base_ip}:5000/cache",
                            ],
                            env=[
                                EnvVar(
                                    "S3_ENDPOINT",
                                    value=f"http://{_base_ip}:{settings.S3_PORT}",
                                ),
                                # need to specify this to use path-stye minio,
                                # and don't try to resolve http://bucket.ip:port/file
                                EnvVar("S3_FORCE_PATH_STYLE", "true"),
                                # i have AWS. Don't work without this
                                EnvVar("AWS_REGION", "us-east-1"),  # i have AWS
                                EnvVar("AWS_ACCESS_KEY_ID", settings.S3_ACCESS),
                                EnvVar("AWS_SECRET_ACCESS_KEY", settings.S3_SECRET),
                            ],
                        ),
                    ],
                    restartPolicy="Never",
                ),
            ),
        )

        if not kaniko.metadata or not kaniko.metadata.name or not kaniko.metadata.namespace:
            raise ImpossibleError

        try:
            kaniko = await self.client.wait(
                Pod,
                kaniko.metadata.name,
                for_conditions=["PodReadyToStartContainers"],
                namespace=kaniko.metadata.namespace,
            )

            if not kaniko.metadata or not kaniko.metadata.name or not kaniko.metadata.namespace or not kaniko.status:
                raise ImpossibleError

            logger.info(
                f"Kaniko pod created: '{kaniko.metadata.namespace}.{kaniko.metadata.name}'",
            )

            async for line in self.client.log(
                kaniko.metadata.name,
                namespace=kaniko.metadata.namespace,
                follow=True,
                newlines=False,
            ):
                logger.info(line)

        finally:
            if not kaniko.metadata or not kaniko.metadata.name or not kaniko.metadata.namespace:
                raise ImpossibleError

            await self.client.delete(Pod, kaniko.metadata.name, namespace=kaniko.metadata.namespace)

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


class KubeConnector(BaseConnector):
    api: KubeApi

    def __init__(self) -> None:
        self.api = KubeApi()
        super().__init__()

    async def init(self) -> None:
        await self.api.init()

    async def test(self) -> None:
        await self.api.test()

    async def close(self) -> None:
        await self.api.close()

    async def start(self, task_info: DynamicTaskInfo) -> None:
        raise NotImplementedError

    async def stop(self, task_info: DynamicTaskInfo) -> None:
        raise NotImplementedError

    async def restart(self, task_info: DynamicTaskInfo) -> None:
        raise NotImplementedError

    async def info(self, task_info: DynamicTaskInfo) -> None:
        raise NotImplementedError
