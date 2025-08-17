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

    global_wtf: AsyncExitStack

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

        self.global_wtf = AsyncExitStack()
        vpn_state = await self.etcd.get_global()
        if not vpn_state or not vpn_state.back_vpn or not vpn_state.back_port:
            raise Exception("bad")

        ns_name, ns = await self.global_wtf.enter_async_context(
            self.api.run_in_ns(
                "vpn",
                annotations={
                    "cni.projectcalico.org/ipv4pools": f'["test-ipv4-pool"]',
                },
            )
        )

        ovpn = await self.api.openvpn_back(
            ns,
            static_key=vpn_state.back_vpn.static_key,
            external_port=vpn_state.back_port,
            stack=self.global_wtf,
        )

    async def test(self) -> None:
        await self.api.test()

    async def close(self) -> None:
        # logger.critical(f"Closing super().KubeConnector")
        await self.global_wtf.aclose()

        await super().close()
        # logger.critical(f"Closed super().KubeConnector, closing api")
        await self.api.close()
        # logger.critical(f"Closed api")

    async def _start(
        self,
        task_info: DynamicTaskInfoBuilding,
        lti: LocalTaskInfo,
        vpn_state: VPNGlobalState,
        vpn_user: VPNUserInfoGenerated,
    ) -> None:
        logger.info(f"Got {task_info = }, resolving path and compose file")

        # TODO: wtf...
        # src = settings.UUID_TO_PATH_MAPPING[task_info.task_id]
        # src = src.resolve()
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
            )
        )

        ipv4pool = await lti.exit_stack.enter_async_context(
            self.api.client.ctx_global(
                self.api.client.simple_ip_pool(
                    f"{ns_name}-v4",
                    cidr=vpn_user.netinfo.task_net.compressed,
                    automatic=False,
                    block_size=29,  # FIXME: hardcode
                ),
            ),
        )

        if not ns.metadata:
            raise Exception

        if not ipv4pool.metadata or not ipv4pool.metadata.name:
            raise Exception

        if not ns.metadata.annotations:
            ns.metadata.annotations = {}

        patch = {
            "metadata": {
                "annotations": {
                    "cni.projectcalico.org/ipv4pools": f'["{ipv4pool.metadata.name}", "test-ipv4-pool"]',
                },
            },
        }
        ns = await self.api.client.patch(type(ns), name=ns_name, obj=patch)

        await self.api.service(
            task_name,
            ns,
            ns_name,
            compose,
            flag=task_info.flag,
            ports_env=lti.ports_env,
            skip_build=False,
            extra_env={"RANDOM_STRING_SEQ": lti.devire_static_random_seq(task_info.flag)},
            ip_in_cluster=vpn_user.netinfo.task_net_task.compressed,
            stack=lti.exit_stack,
            extra_route=("10.10.0.0/16", vpn_user.netinfo.task_net_vpn.compressed),
        )

        # fff = next(iter(settings.EXTERNAL_TO_INTERNAL_IPS_MAPPING.values()))
        # ovpn, svc = await self.api.openvpn(
        #     ns,
        #     usernet=vpn_user.netinfo,
        #     static_key=vpn_user.task.static_key,
        #     external_ips=fff,
        #     stack=lti.exit_stack,
        # )

    async def _start_vm(
        self,
        task_info: DynamicTaskInfoBuilding,
        lti: LocalTaskInfo,
        vpn_state: VPNGlobalState,
        vpn_user: VPNUserInfoGenerated,
    ):
        logger.info(f"Got {task_info = }, doing work")

        name = f"{task_info.encoded_task_id}-{task_info.encoded_user_id}"

        src = await self.unpack_data(task_info, lti, service=False)

        # extra_env = {
        #     "FLAG": task_info.flag,
        #     "RANDOM_STRING_SEQ": lti.devire_static_random_seq(task_info.flag),
        # }

        with TemporaryDirectory(prefix=f"yatb-build-vm.docker.{task_info.task_id!s}.") as dest:
            dest = Path(dest)
            docker = dest / "Dockerfile"
            docker.write_text(f"FROM scratch\nADD  --chown=107:107 {task_info.s3_link} /disk/drive.qcow2")
            os.utime(docker, (0, 0))

            vm_image = await self.api.build(
                f"{task_info.encoded_task_id}-image",
                dest,
            )

        customize = await self.api.build(
            f"{name}-customize",
            src,
            kaniko_args=[
                f"--build-arg=FLAG={task_info.flag}",
            ],
        )

        ns_name, ns = await lti.exit_stack.enter_async_context(
            self.api.run_in_ns(
                f"{task_info.encoded_task_id}",
                annotations={
                    "rubikoid.ru/dtc-user-id": f"{task_info.user_id!s}",
                    "rubikoid.ru/dtc-task-id": f"{task_info.task_id!s}",
                },
            )
        )

        ipv4pool = await lti.exit_stack.enter_async_context(
            self.api.client.ctx_global(
                self.api.client.simple_ip_pool(
                    f"{ns_name}-v4",
                    cidr=vpn_user.netinfo.task_net.compressed,
                    automatic=False,
                    block_size=29,  # FIXME: hardcode
                ),
            ),
        )

        if not ns.metadata:
            raise Exception

        if not ipv4pool.metadata or not ipv4pool.metadata.name:
            raise Exception

        if not ns.metadata.annotations:
            ns.metadata.annotations = {}

        patch = {
            "metadata": {
                "annotations": {
                    "cni.projectcalico.org/ipv4pools": f'["{ipv4pool.metadata.name}", "test-ipv4-pool"]',
                },
            },
        }
        ns = await self.api.client.patch(type(ns), name=ns_name, obj=patch)

        vm = await lti.exit_stack.enter_async_context(
            self.api.client.ctx(
                self.api.client.simple_vm(
                    name="vm",
                    namespace=ns_name,
                    ip_in_cluster=vpn_user.netinfo.task_net_task.compressed,
                    image=self.api.fix_image_name(vm_image),
                    custm=self.api.fix_image_name(customize),
                    cpu=6 if not task_info.user_admin else 12,
                    memory="2.5Gi" if not task_info.user_admin else "4Gi",
                ),
            ),
        )

        # fff = next(iter(settings.EXTERNAL_TO_INTERNAL_IPS_MAPPING.values()))
        # ovpn, svc = await self.api.openvpn(
        #     ns,
        #     usernet=vpn_user.netinfo,
        #     static_key=vpn_user.task.static_key,
        #     external_ips=fff,
        #     stack=lti.exit_stack,
        # )

    async def _build(self, task_info: DynamicTaskInfoBuilding, lti: LocalTaskInfo) -> str:
        logger.info(f"Got {task_info = } to build")

        # src = settings.UUID_TO_PATH_MAPPING[task_info.task_id]
        # src = src.resolve().parent / "dev"
        src = await self.unpack_data(task_info, lti, service=False)

        # TODO: WTF
        hp = lti.ports_env.tracking_ports[0]

        extra_env = {
            "FLAG": task_info.flag,
            "BACKEND_HOST": hp.host,
            "BACKEND_PORT": str(hp.port),
            "RANDOM_STRING_SEQ": lti.devire_static_random_seq(task_info.flag),
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
