import os
import tarfile
from contextlib import AsyncExitStack
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from loguru import logger

from yatb.shared.dtc.models import DynamicTaskInfoBase, DynamicTaskInfoBuilding, VPNGlobalState, VPNUserInfoGenerated

from ...config import settings
from ...controllers import ExpirationController, PortsController
from .. import BaseConnector, DynamicTaskInfo, LocalTaskInfo
from ..compose import Compose, load_compose
from .api import KubeApi


class KubeConnector(BaseConnector):
    api: KubeApi

    def __init__(
        self,
        *,
        run_workers: bool = settings.DO_WORK,
    ) -> None:  # , expiration_controller: ExpirationController, ports_controller: PortsController) -> None:
        self.api = KubeApi()

        # FIXME: temp for dev
        expiration_controller = ExpirationController()
        ports_controller = PortsController()

        super().__init__(
            expiration_controller=expiration_controller,
            ports_controller=ports_controller,
            run_workers=run_workers,
        )

    async def init(self) -> None:
        await self.api.init()

    async def close(self) -> None:
        # logger.critical(f"Closing super().KubeConnector")
        await super().close()
        # logger.critical(f"Closed super().KubeConnector, closing api")
        await self.api.close()
        # logger.critical(f"Closed api")

    async def _start(
        self,
        task_info: DynamicTaskInfoBuilding,
        lti: LocalTaskInfo,
    ) -> None:
        logger.info(f"Got {task_info = }, resolving path and compose file")

        src = await self.unpack_data(task_info, lti, service=True)

        compose = load_compose(src)

        task_name = task_info.encoded_task_id
        ns_name, ns = await lti.exit_stack.enter_async_context(
            self.api.run_in_ns(
                f"{task_name}",
                annotations={
                    "rubikoid.ru/dtc-user-id": f"{task_info.user_id!s}",
                    "rubikoid.ru/dtc-task-id": f"{task_info.task_id!s}",
                },
            ),
        )

        if not ns.metadata:
            raise Exception

        if not ns.metadata.annotations:
            ns.metadata.annotations = {}

        await self.api.service(
            task_name,
            ns,
            ns_name,
            compose,
            flag=task_info.flag,
            ports_env=lti.ports_env,
            skip_build=False,
            extra_env={"RANDOM_STRING_SEQ": lti.devire_static_random_seq(task_info.flag)},
            stack=lti.exit_stack,
        )

    async def _start_vm(
        self,
        task_info: DynamicTaskInfoBuilding,
        lti: LocalTaskInfo,
    ):
        logger.info(f"Got {task_info = }, doing work")

        # name = f"{task_info.encoded_task_id}-{task_info.encoded_user_id}"

        # src = await self.unpack_data(task_info, lti, service=False)

        # extra_env = {
        #     "FLAG": task_info.flag,
        #     "RANDOM_STRING_SEQ": lti.devire_static_random_seq(task_info.flag),
        # }

        with TemporaryDirectory(prefix=f"yatb-build-vm.docker.{task_info.task_id!s}.") as dest:
            dest = Path(dest)

            # logger.info(f"Extracting {task_info.task_id}/image.qcow2")

            # image = dest / "image.qcow2"
            # object = await self.api.s3.get_object(
            #     settings.TASKS_BUCKET_NAME,
            #     object_name=f"{task_info.task_id}/image.qcow2",
            #     session=None,
            # )
            # with image.open("wb") as f:
            #     async for data, _ in object.content.iter_chunks():
            #         f.write(data)
            # os.utime(image, (0, 0))

            docker = dest / "Dockerfile"
            docker.write_text(f"FROM scratch\nADD  --chown=107:107 {task_info.s3_link} /disk/drive.qcow2")
            os.utime(docker, (0, 0))

            vm_image = await self.api.build(
                f"{task_info.encoded_task_id}-image",
                dest,
                force_rebuild=task_info.force_rebuild,  # WTF: ... ;(
            )

        # customize = await self.api.build(
        #     f"{name}-customize",
        #     src,
        #     kaniko_args=[
        #         f"--build-arg=FLAG={task_info.flag}",
        #     ],
        # )

        ns_name, ns = await lti.exit_stack.enter_async_context(
            self.api.run_in_ns(
                f"{task_info.encoded_task_id}",
                annotations={
                    "rubikoid.ru/dtc-user-id": f"{task_info.user_id!s}",
                    "rubikoid.ru/dtc-task-id": f"{task_info.task_id!s}",
                },
            )
        )

        ports = task_info.vm_ports
        for port in ports:
            public_hp = await lti.ports_env.get_port()
            service = self.api.client.ctx(
                self.api.client.simple_service(
                    f"vm",
                    ns_name,
                    public_hp.port,
                    port,
                    settings.EXTERNAL_TO_INTERNAL_IPS_MAPPING[public_hp.host],
                    name_suffix=f"-p{port}-public",
                    # selector="vm.kubevirt.io/name",
                    selector="kubevirt.io/domain",
                ),
            )
            service = await lti.exit_stack.enter_async_context(service)

        user_data: dict = {
            "write_files": [
                {
                    "content": task_info.flag,
                    "path": "/flag",
                    "owner": "root:root",
                    "permissions": "0400",
                },
            ],
        }
        if task_info.user_admin:
            user_data["users"] = [
                {
                    "name": "root",
                    "lock_passwd": False,
                    # 1
                    "hashed_passwd": "$6$rounds=4096$rS3t4SotwWPRb6J7$8nzYAf8ZHTZi60MUIFikUoKLmQWDfTxUGjZWXfbTNk42sCFcF2JmZWjLriBN0AFLACggCVFprgQyaKj1Mw1oW1",
                    "ssh_authorized_keys": [],
                },
            ]

        vm = await lti.exit_stack.enter_async_context(
            self.api.client.ctx(
                self.api.client.simple_vm(
                    name="vm",
                    namespace=ns_name,
                    # ip_in_cluster=vpn_user.netinfo.task_net_task.compressed,
                    image=self.api.fix_image_name(vm_image),
                    # custm=self.api.fix_image_name(customize),
                    cpu=2 if not task_info.user_admin else 4,
                    memory="2.5Gi" if not task_info.user_admin else "4Gi",
                    user_data_raw=user_data,
                ),
            ),
        )

    async def _build(self, task_info: DynamicTaskInfoBuilding, lti: LocalTaskInfo) -> str:
        logger.info(f"Got {task_info = } to build")

        # src = settings.UUID_TO_PATH_MAPPING[task_info.task_id]
        # src = src.resolve().parent / "dev"
        src = await self.unpack_data(task_info, lti, service=False)

        extra_env = {
            "FLAG": task_info.flag,
            "RANDOM_STRING_SEQ": lti.devire_static_random_seq(task_info.flag),
        }

        if lti.ports_env.tracking_ports:
            # TODO: WTF
            hp = lti.ports_env.tracking_ports[0]
            extra_env |= {
                "BACKEND_HOST": hp.host,
                "BACKEND_PORT": str(hp.port),
            }

        path = await self.api.oneshot(
            task_info.name,
            src,
            env=extra_env,
            s3_prefix=f"{task_info.encoded_user_id}/{task_info.encoded_task_id}",
        )

        return f"{settings.S3_PROXY_HOST}/{path}"

    async def unpack_data(self, task_info: DynamicTaskInfoBuilding, lti: LocalTaskInfo, *, service: bool) -> Path:
        # FIXME: hardcode?)
        info = task_info.service_info if service else task_info.builder_info
        if not info:
            raise Exception("err")

        dest = TemporaryDirectory(prefix=f"yatb-build.{service}.{task_info.task_id!s}.{info[1]}.")
        dest = Path(lti.exit_stack.enter_context(dest))

        object = await self.api.s3.get_object(
            settings.TASKS_BUCKET_NAME,
            object_name=info[0],
            session=None,
        )

        content = await object.content.read()
        with tarfile.open(fileobj=BytesIO(content), mode="r:gz") as tar:
            tar.extractall(dest, filter="data")

        return dest
