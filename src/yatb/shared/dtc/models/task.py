import datetime
from enum import CONFORM, Flag, StrEnum, auto
from typing import Annotated, Literal, Self, TypeGuard
from uuid import UUID

from pydantic import BaseModel, Field, RootModel

from .... import schema
from .base import BaseETCDModel


class DynamicTaskFeatures(Flag, boundary=CONFORM):
    # it's important to order SERVICE, BUILDER here
    # because in building service AND builder, whe should firstly start service and
    # only than build thing with kinda addr of backed or so
    NONE = 0

    SERVICE = auto()
    VM = auto()
    VPN = auto()
    BUILDER = auto()


class DynamicTaskQuery(StrEnum):
    EXTEND = auto()
    RESTART = auto()
    STOP = auto()


class DynamicTaskQueryStatus(StrEnum):
    TASK_NOT_FOUND = auto()
    ALREADY_IN_PROGRESS = auto()
    REQUESTED = auto()


class DynamicTaskState(StrEnum):
    PREPARED = auto()
    BUILDING = auto()
    READY = auto()
    DELETING = auto()


class HostPortPair(BaseModel):
    host: str
    port: int


class DynamicTaskInfoBase(BaseETCDModel):
    state: Literal[DynamicTaskState.PREPARED] = DynamicTaskState.PREPARED

    name: str
    task_id: UUID

    features: DynamicTaskFeatures

    user_id: UUID
    user_admin: bool = False

    flag: str

    service_info: tuple[str, str] | None = None
    builder_info: tuple[str, str] | None = None
    s3_link: str | None

    @classmethod
    def build(cls, task: "schema.Task", user: "schema.User") -> Self:
        if not task.dti:
            raise Exception("impossible")

        return cls(
            name=f"{task.task_id}",
            task_id=task.task_id,
            features=task.dti.features,
            user_id=user.user_id,
            user_admin=user.is_admin,
            flag=task.flag.flag_value(user),
            service_info=task.dti.service_info,
            builder_info=task.dti.builder_info,
            s3_link=task.dti.s3_url,
        )

    @property
    def encoded_task_id(self) -> str:
        return self.encode(f"{self.task_id!s}")

    @property
    def encoded_user_id(self) -> str:
        return self.encode(f"{self.user_id!s}")


class DynamicTaskInfoBuilding(DynamicTaskInfoBase):
    state: Literal[DynamicTaskState.BUILDING] = DynamicTaskState.BUILDING

    hps: list[HostPortPair] = []
    static_link: str | None = None

    expiration_id: UUID | None = None
    time_of_death: datetime.datetime | None = None


class DynamicTaskInfoReady(DynamicTaskInfoBase):
    state: Literal[DynamicTaskState.READY] = DynamicTaskState.READY

    hps: list[HostPortPair] = []
    static_link: str | None = None

    expiration_id: UUID
    time_of_death: datetime.datetime


class DynamicTaskInfoDeleting(DynamicTaskInfoReady):
    state: Literal[DynamicTaskState.DELETING] = DynamicTaskState.DELETING


DynamicTaskInfo = Annotated[
    DynamicTaskInfoBase | DynamicTaskInfoBuilding | DynamicTaskInfoReady | DynamicTaskInfoDeleting,
    Field(
        ...,
        discriminator="state",
    ),
]

DynamicTaskInfoModel = RootModel[DynamicTaskInfo]


def is_taskinfo_prepared(t: DynamicTaskInfo) -> TypeGuard["DynamicTaskInfoBase"]:
    return t.state == DynamicTaskState.PREPARED


def is_taskinfo_building(t: DynamicTaskInfo) -> TypeGuard["DynamicTaskInfoBuilding"]:
    return t.state == DynamicTaskState.BUILDING


def is_taskinfo_ready(t: DynamicTaskInfo) -> TypeGuard["DynamicTaskInfoReady"]:
    return t.state == DynamicTaskState.READY


def is_taskinfo_deleting(t: DynamicTaskInfo) -> TypeGuard["DynamicTaskInfoDeleting"]:
    return t.state == DynamicTaskState.DELETING
