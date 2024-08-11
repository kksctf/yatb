import datetime
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from dataclasses import dataclass
from enum import Enum
from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel

from ..controllers import ExpirationController, PortsController
from ..controllers.ports_controller import HostPortPair
from .errors import GenericConnectorError


class DynamicTaskType(Enum):
    BUILDER = "builder"
    SERVICE = "service"


class DynamicTaskInfo(BaseModel):
    name: str
    descriptor: UUID

    type: DynamicTaskType

    user_id: str


@dataclass
class LocalTaskInfo:
    id: UUID

    task_descriptor: UUID
    user_id: str

    _info: DynamicTaskInfo

    expiration_id: UUID | None = None
    hp: HostPortPair | None = None

    @property
    def hp_ok(self) -> HostPortPair:
        if not self.hp:
            raise Exception
        return self.hp

    @property
    def expiration_id_ok(self) -> UUID:
        if not self.expiration_id:
            raise Exception
        return self.expiration_id

    @classmethod
    def build(
        cls,
        info: DynamicTaskInfo,
    ) -> Self:
        return cls(
            id=uuid4(),
            task_descriptor=info.descriptor,
            user_id=info.user_id,
            _info=info,
        )


class ExternalDynamicTaskInfo(BaseModel):
    id: UUID

    task_descriptor: UUID

    user_id: str

    hp: HostPortPair

    least_time: datetime.timedelta


class BaseConnector(ABC):
    tasks: dict[UUID, LocalTaskInfo]
    tasks_index: dict[tuple[UUID, str], LocalTaskInfo]

    expiration_controller: ExpirationController
    ports_controller: PortsController

    def __init__(self, expiration_controller: ExpirationController, ports_controller: PortsController) -> None:
        super().__init__()

        self.tasks = {}
        self.tasks_index = {}

        self.expiration_controller = expiration_controller
        self.ports_controller = ports_controller

    async def __aenter__(self) -> Self:
        await self.init()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        await self.ports_controller.close()
        await self.expiration_controller.close()

    @abstractmethod
    async def _start(self, task_info: LocalTaskInfo) -> AsyncExitStack:
        raise NotImplementedError

    @abstractmethod
    async def _stop(self, task_info: LocalTaskInfo) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _restart(self, task_info: LocalTaskInfo) -> None:
        raise NotImplementedError

    async def _info(self, ltask_info: LocalTaskInfo) -> ExternalDynamicTaskInfo:
        expiration_info = self.expiration_controller.get(ltask_info.expiration_id_ok)

        return ExternalDynamicTaskInfo(
            id=ltask_info.id,
            task_descriptor=ltask_info.task_descriptor,
            user_id=ltask_info.user_id,
            hp=ltask_info.hp_ok,
            least_time=expiration_info.time_left,
        )

    def init_ltask_info(self, task_info: DynamicTaskInfo) -> LocalTaskInfo:
        k = (task_info.descriptor, task_info.user_id)

        if k in self.tasks_index:
            raise GenericConnectorError("This task for your team already exsits")

        self.tasks_index[k] = LocalTaskInfo.build(task_info)
        return self.tasks_index[k]

    def get_ltask_info(self, task_info: DynamicTaskInfo) -> LocalTaskInfo:
        k = (task_info.descriptor, task_info.user_id)

        if k not in self.tasks_index:
            raise GenericConnectorError("No task found")

        return self.tasks_index[k]

    def free_ltask_info(self, task_info: DynamicTaskInfo) -> None:
        k = (task_info.descriptor, task_info.user_id)

        del self.tasks_index[k]

    async def start(self, task_info: DynamicTaskInfo) -> ExternalDynamicTaskInfo:
        ltask_info = self.init_ltask_info(task_info)
        ltask_info.hp = self.ports_controller.get_host_and_port()

        logger.info(f"Got port {ltask_info.hp = }")

        stack = await self._start(ltask_info)
        stack.callback(lambda: self.ports_controller.free_port(ltask_info.hp_ok))
        stack.callback(lambda: self.free_ltask_info(task_info))

        info = await self.expiration_controller.push_stack(stack)
        logger.info(f"Pushed {info = }")
        ltask_info.expiration_id = info.id

        return await self._info(ltask_info)

    async def stop(self, task_info: DynamicTaskInfo) -> None:
        ltask_info = self.get_ltask_info(task_info)
        await self._restart(ltask_info)

    async def restart(self, task_info: DynamicTaskInfo) -> None:
        ltask_info = self.get_ltask_info(task_info)
        await self._restart(ltask_info)

    async def extend(self, task_info: DynamicTaskInfo) -> None:
        ltask_info = self.get_ltask_info(task_info)
        self.expiration_controller.extend_life(ltask_info.expiration_id_ok, datetime.timedelta(minutes=1))

    async def info_task(self, task_info: DynamicTaskInfo) -> ExternalDynamicTaskInfo:
        ltask_info = self.get_ltask_info(task_info)
        return await self._info(ltask_info)

    async def info_id(self, dynamic_task_id: UUID) -> ExternalDynamicTaskInfo:
        ltask_info = self.tasks[dynamic_task_id]
        return await self._info(ltask_info)
