from contextlib import AsyncExitStack
from pathlib import Path

from lightkube.models.core_v1 import (
    Container,
    EnvVar,
    PersistentVolumeClaimVolumeSource,
    PodSpec,
    Volume,
    VolumeMount,
)
from lightkube.models.core_v1 import ResourceRequirements as kResourceRequirements
from lightkube.types import CascadeType
from loguru import logger
from miniopy_async.datatypes import Object

from dtc.config import settings

from ..client import ImpossibleError, check_meta
from .base import KubeApiBase

_base_path = Path(__file__).parent.parent


class KubeApiOneshot(KubeApiBase):
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
            source=_base_path.parent.parent / "extra" / "builder",
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
            ]
            volume_mounts = [
                VolumeMount(
                    name="build-volume",
                    mountPath=_EXPORT_PATH,
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
                                    f"{settings.S3_PORT_KANIKO}",
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

                full_log: str = ""

                async for log in self.client.log(
                    job_pod.metadata.name,
                    namespace=job_pod.metadata.namespace,
                    newlines=False,
                ):
                    full_log += log
                    if log.endswith("uploaded"):
                        frm = log.index("'")
                        to = log.index("'", frm + 1)
                        parsed_log = log[frm + 1 : to]

                        logger.info(f"{log = } -> {parsed_log = }, {frm = }, {to = }")
                        break  # TODO: make this better
                else:
                    raise Exception("error building shit", full_log)

        return f"{parsed_log}"
