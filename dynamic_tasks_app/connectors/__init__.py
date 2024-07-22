from abc import ABC, abstractmethod
from enum import Enum
from types import TracebackType
from typing import AsyncContextManager, Self
from uuid import UUID

from pydantic import BaseModel


class DynamicTaskType(Enum):
    BUILDER = "builder"
    SERVICE = "service"


class DynamicTaskInfo(BaseModel):
    descriptor: UUID
    type: DynamicTaskType

    user_id: str


class BaseConnector(ABC):
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
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def start(self, task_info: DynamicTaskInfo) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop(self, task_info: DynamicTaskInfo) -> None:
        raise NotImplementedError

    @abstractmethod
    async def restart(self, task_info: DynamicTaskInfo) -> None:
        raise NotImplementedError

    @abstractmethod
    async def info(self, task_info: DynamicTaskInfo) -> None:
        raise NotImplementedError
