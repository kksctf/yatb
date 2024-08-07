from contextlib import AsyncExitStack

from loguru import logger

from ...config import settings
from ...controllers import ExpirationController, PortsController
from .. import BaseConnector, DynamicTaskInfo, LocalTaskInfo
from ..compose import Compose, load_compose
from .api import KubeApi


class KubeConnector(BaseConnector):
    api: KubeApi

    def __init__(
        self,
    ) -> None:  # , expiration_controller: ExpirationController, ports_controller: PortsController) -> None:
        self.api = KubeApi()
        # FIXME: temp for dev
        expiration_controller = ExpirationController()
        ports_controller = PortsController()
        super().__init__(expiration_controller=expiration_controller, ports_controller=ports_controller)

    async def init(self) -> None:
        await self.api.init()

    async def test(self) -> None:
        await self.api.test()

    async def close(self) -> None:
        await super().close()
        await self.api.close()

    async def _start(self, task_info: LocalTaskInfo) -> AsyncExitStack:
        logger.info(f"Got {task_info = }, resolving path and compose file")

        src = settings.UUID_TO_PATH_MAPPING[task_info.task_descriptor]
        src = src.resolve()

        compose = load_compose(src)

        logger.info(f"Loaded {compose = }")

        return await self.api.service(
            task_info._info.name,
            compose,
            flag="crab{test}",
            host=task_info.hp_ok.host,
            port=task_info.hp_ok.port,
            skip_build=True,
        )

    async def _stop(self, task_info: LocalTaskInfo) -> None:
        raise NotImplementedError

    async def _restart(self, task_info: LocalTaskInfo) -> None:
        raise NotImplementedError
