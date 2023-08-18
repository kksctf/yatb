import uuid
from typing import ClassVar, Generic, Hashable, Self, TypeVar, final
from pydantic import ConfigDict

import pymongo
from beanie import Document, init_beanie
from beanie.odm.operators.find.logical import And as _And
from motor.motor_asyncio import AsyncIOMotorClient

from app.schema.ebasemodel import FilterFieldsType

from .. import app, schema
from ..schema import Task, User
from ..utils.log_helper import get_logger

logger = get_logger("db.beanie")

_T = TypeVar("_T", bound=schema.EBaseModel)


class DocumentEx(Document, schema.EBaseModel, Generic[_T]):
    @final
    @classmethod
    def build_model(
        cls: type[Self],
        include: FilterFieldsType,
        exclude: FilterFieldsType,
        name: str = "sub",
        *,
        public: bool = True,
    ) -> type[Self]:
        return cls

    @classmethod
    def make_db_model(cls: type[Self], base: _T) -> Self:
        return cls.model_validate(base, from_attributes=True)


class TaskDB(DocumentEx[Task], Task):
    @classmethod
    async def find_by_task_uuid(cls: type[Self], task_id: uuid.UUID) -> Self | None:
        return await cls.find_one(cls.task_id == task_id)

    @classmethod
    async def get_all(cls: type[Self]) -> dict[uuid.UUID, Self]:
        return {i.task_id: i for i in await cls.find_all().to_list()}

    class Settings:
        name: ClassVar = "tasks"
        indexes: ClassVar = [
            [
                ("task_id", pymongo.ASCENDING),
            ],
        ]


class UserDB(DocumentEx[User], User):
    @classmethod
    async def find_by_user_uuid(cls: type[Self], task_id: uuid.UUID) -> Self | None:
        return await cls.find_one(cls.user_id == task_id)

    @classmethod
    async def find_by_username(cls: type[Self], username: str) -> Self | None:
        return await cls.find_one(cls.username == username)

    @classmethod
    async def get_all(cls: type[Self]) -> dict[uuid.UUID, Self]:
        return {i.user_id: i for i in await cls.find_all().to_list()}

    @classmethod
    async def get_user_uniq_field(
        cls: type[Self],
        base: type[schema.auth.AuthBase],
        field: Hashable,
    ) -> Self | None:
        return await cls.find_one(
            _And(
                cls.auth_source.classtype
                == base.__name__,  # FIXME: __name__ there bc pydantic https://github.com/pydantic/pydantic/issues/7179
                {base.AuthModel.get_uniq_field_name(): field},
            ),
        )

    class Settings:
        name: ClassVar = "users"
        indexes: ClassVar = [
            [
                ("user_id", pymongo.ASCENDING),
            ],
        ]


class DBClient:
    client: AsyncIOMotorClient  # type: ignore

    def __init__(self) -> None:
        pass

    async def init(self) -> None:
        self.client = AsyncIOMotorClient("mongodb://root:root@127.0.0.1:27017")
        await init_beanie(database=self.client.yatb, document_models=[TaskDB, UserDB])  # type: ignore
        logger.info("Beanie init ok")

    async def close(self) -> None:
        logger.info("DB close ok")


@app.on_event("startup")
async def startup_event():
    await db.init()


@app.on_event("shutdown")
async def shutdown_event():
    await db.close()


# async def init_db():
#     await db.init()
#     yield
#     await db.close()


db = DBClient()
