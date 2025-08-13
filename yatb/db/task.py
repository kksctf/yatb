import datetime
import uuid
from collections.abc import Hashable, Mapping
from typing import Any, ClassVar, Literal, Self

import pymongo
from beanie import BulkWriter, Document, init_beanie
from beanie.operators import And as _And
from beanie.operators import Set
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel

from yatb.config import settings
from yatb.ebasemodelv2 import EBaseModelV2
from yatb.schema import FlagCheckResult, Task, TaskForm, User, auth
from yatb.utils.log_helper import get_logger

from .base import DocumentEx

logger = get_logger("db.task")


class TaskDB(DocumentEx[Task], Task):
    # pwned_by: dict[Annotated[uuid.UUID, SER_UUID], datetime.datetime] = {}

    async def update_entry(self, new_task: Task) -> Self:
        logger.debug(f"Update task {self} to {new_task}")

        # WTF: концептуально, но не уверен, что можно лучше.
        self.update_entry_raw(
            new_task.model_dump(
                exclude={
                    "task_id",
                    "description_html",
                    "scoring",
                    "flag",
                    "pwned_by",
                },
            ),
        )

        # task.scoring = new_task.scoring  # fix for json-ing scoring on edit
        # task.flag = new_task.flag  # fix for json-ing flag on edit

        logger.debug(f"Resulting task={self}")
        self.description_html = Task.regenerate_md(self.description)

        await self.save()

        return self

    @classmethod
    async def populate(cls, new_task: TaskForm, author: User) -> Self:
        task = new_task.to_task(cls, author)
        await task.insert()
        return task

    @classmethod
    async def find_by_task_uuid(cls: type[Self], task_id: uuid.UUID) -> Self | None:
        return await cls.find_one(cls.task_id == task_id)

    @classmethod
    async def get_all(cls: type[Self]) -> dict[uuid.UUID, Self]:
        return {i.task_id: i for i in await cls.find_all().to_list()}

    @classmethod
    async def find_by_flag(cls: type[Self], flag: str, user: User) -> Self | None:
        for task in await cls.find_all().to_list():
            result = task.flag.flag_checker(flag, user)
            if result == FlagCheckResult.valid:
                return task

            if result == FlagCheckResult.invalid:
                continue

            logger.warning(f"user=[{user.short_desc()}], task=[{task.short_desc()}], {flag=}, {result.name=}")

        return None

    @classmethod
    async def recalc_score(cls: type[Self]) -> None:
        async with BulkWriter() as bw:
            for task in (await cls.get_all()).values():
                task.scoring.set_solves(len(task.pwned_by))
                await task.update(
                    Set(
                        {str(TaskDB.scoring): task.scoring},
                    ),
                    bulk_writer=bw,
                )
            logger.info(bw.operations)

    class Settings:
        name: ClassVar = "tasks"
        indexes: ClassVar = [
            [
                ("task_id", pymongo.ASCENDING),
            ],
        ]
