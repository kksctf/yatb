import uuid
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, RootModel

from yatb import schema
from yatb.config import settings as yatb_settings


class DynamicTaskFeatures(StrEnum):
    SERVICE = "service"
    VM = "vm"
    VPN = "vpn"
    BUILDER = "builder"

    def to_schema(self) -> schema.DynamicTaskFeatures:
        match self:
            case self.SERVICE:
                return schema.DynamicTaskFeatures.SERVICE
            case self.VM:
                return schema.DynamicTaskFeatures.VM
            case self.VPN:
                return schema.DynamicTaskFeatures.VPN
            case self.BUILDER:
                return schema.DynamicTaskFeatures.BUILDER


if len(DynamicTaskFeatures) == len(schema.DynamicTaskFeatures):
    raise Exception(f"{len(DynamicTaskFeatures) == len(schema.DynamicTaskFeatures) = } ???")  # noqa: TRY002


class FileTask(BaseModel):
    name: str
    description: str

    author: str
    category: str

    flag: str

    dynamic_scoring: bool = False

    dynamic_features: list[DynamicTaskFeatures] = []

    hidden: bool = True

    @property
    def full_features(self) -> schema.DynamicTaskFeatures:
        ret: schema.DynamicTaskFeatures = schema.DynamicTaskFeatures.NONE

        for feature in self.dynamic_features:
            ret |= feature.to_schema()

        return ret

    def get_flag(self) -> schema.FlagUnion:
        flag = self.flag
        flag_base = yatb_settings.FLAG_BASE

        # normalize flag_base?)0
        if "{" in flag and "}" in flag and not flag.startswith(flag_base):
            flag_base = flag[: flag.index("{")]

        if flag.startswith(flag_base + "{") and flag.endswith("}"):
            flag = flag.removeprefix(flag_base + "{")
            flag = flag.removesuffix("}")

        if self.dynamic_features:
            flag_model = schema.flags.DynamicKKSFlag(dynamic_flag_base=flag, flag_base=flag_base)
        else:
            flag_model = schema.flags.StaticFlag(flag=flag, flag_base=flag_base)

        return flag_model

    def get_form(
        self,
        *,
        old_task_uuid: uuid.UUID | None = None,
        req_tasks: Sequence[uuid.UUID] = [],
    ) -> schema.TaskForm:
        description = self.description.strip().strip('"').strip("'")

        if self.dynamic_scoring:  # noqa: SIM108
            scoring = schema.DynamicKKSScoring()
        else:
            scoring = schema.StaticScoring(static_points=1337)

        return schema.TaskForm(
            task_id=old_task_uuid,
            task_name=self.name,
            category=self.category,
            scoring=scoring,
            description=description,
            flag=self.get_flag(),
            author=self.author,
            dti=schema.DynamicTaskInfo(features=self.full_features),
            req_tasks=req_tasks,
        )


class State(BaseModel):
    task_to_uuid: dict[Path, uuid.UUID] = {}

    @property
    def uuid_to_task(self) -> dict[uuid.UUID, Path]:
        return {v: i for i, v in self.task_to_uuid.items()}

    @classmethod
    @asynccontextmanager
    async def get(cls, state_path: Path) -> AsyncGenerator[Self]:
        state = cls.model_validate_json(state_path.read_text()) if state_path.exists() else cls()
        try:
            yield state
        finally:
            state_path.write_text(state.model_dump_json(indent=4))


AllUsers = RootModel[dict[uuid.UUID, schema.User.admin_model]]
AllTasks = RootModel[dict[uuid.UUID, schema.Task.admin_model]]
