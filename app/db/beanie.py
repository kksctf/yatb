import datetime
import uuid
from collections.abc import Hashable, Mapping
from typing import Annotated, Any, ClassVar, Generic, Literal, Self, TypeVar, final

import bson
import pymongo
from beanie import BulkWriter, Document, init_beanie
from beanie.operators import And as _And
from beanie.operators import Set
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import PlainSerializer

from .. import app
from ..config import settings
from ..schema import EBaseModel, Task, TaskForm, User, auth
from ..schema.ebasemodel import FilterFieldsType
from ..utils.log_helper import get_logger

logger = get_logger("db.beanie")

_T = TypeVar("_T", bound=EBaseModel)
_TT = TypeVar("_TT", bound=EBaseModel)

# SER_UUID = PlainSerializer(lambda x: bson.Binary.from_uuid(x), return_type=bson.Binary, when_used="json")
# SER_UUID = PlainSerializer(lambda x: str, return_type=str, when_used="json")


class DocumentEx(Document, EBaseModel, Generic[_T]):
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

    def update_entry_raw(self, data: dict[str, Any]) -> None:
        for i, v in data.items():
            if i in self.model_fields:
                setattr(self, i, v)

    @staticmethod
    def sanitize_dict(d: dict[uuid.UUID, datetime.datetime]) -> dict[str, datetime.datetime]:
        return {str(i): v for i, v in d.items()}


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

        await self.save()  # type: ignore # WTF: bad library

        return self

    @classmethod
    async def populate(cls: type[Self], new_task: TaskForm, author: User) -> Self:
        task = cls(
            task_name=new_task.task_name,
            category=new_task.category,
            scoring=new_task.scoring,
            description=new_task.description,
            description_html=Task.regenerate_md(new_task.description),
            flag=new_task.flag,
            author=(new_task.author if new_task.author != "" else f"@{author.username}"),
        )
        await task.insert()  # type: ignore # WTF: bad library
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
            if task.flag.flag_checker(flag, user):
                return task

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


class UserDB(DocumentEx[User], User):
    # solved_tasks: dict[Annotated[uuid.UUID, SER_UUID], datetime.datetime] = {}

    class ScoreboardProjection(EBaseModel):
        user_id: uuid.UUID
        username: str
        score: int
        solved_tasks: dict[uuid.UUID, datetime.datetime]
        is_admin: bool

        def get_last_solve_time(self) -> tuple[uuid.UUID, datetime.datetime] | tuple[Literal[""], datetime.datetime]:
            if len(self.solved_tasks) > 0:
                return max(self.solved_tasks.items(), key=lambda x: x[1])

            return ("", datetime.datetime.fromtimestamp(0, tz=datetime.UTC))

    async def recalc_score_one(self) -> None:
        # WTF: db_lock?
        task_cache = await TaskDB.get_all()

        async with BulkWriter() as bw:
            await self.recalc_score(task_cache, bw=bw)
            logger.info(bw.operations)

    async def recalc_score(self, _task_cache: Mapping[uuid.UUID, Task | None], bw: BulkWriter) -> None:
        # WTF: db_lock?

        old_score = self.score

        self.score = 0
        for task_id in self.solved_tasks:
            # if task_id not in _task_cache:
            #     task = _task_cache[task_id] = await TaskDB.find_by_task_uuid(task_id)
            # else:

            task = _task_cache.get(task_id, None)
            if not task:
                logger.warning(f"Unkonwn task: {task_id =} in {self.short_desc()}")
                continue

            self.score += task.scoring.points
            # task.scoring.set_solves(len(task.pwned_by)) # WTF: should I..?

        if old_score != self.score:
            logger.warning(f"Recalc: smth wrong with {self.short_desc()}, {old_score} != {self.score}!")
            # don't update score, if it not changed
            await self.update(Set({UserDB.score: self.score}), bulk_writer=bw)

    async def solve_task_bw(self, task: TaskDB) -> uuid.UUID:
        async with BulkWriter() as bw:
            ret = await self.solve_task(task, bw=bw)
            logger.info(bw.operations)

        return ret

    async def solve_task(self, task: TaskDB, bw: BulkWriter) -> uuid.UUID:
        # if you admin - you can check flag parsing/task search, but do not affect scoreboard.
        if self.is_admin and not settings.DEBUG:
            return task.task_id

        if datetime.datetime.now(tz=datetime.UTC) > settings.EVENT_END_TIME:
            return task.task_id

        # WTF: db_lock?

        # add references
        solve_time = datetime.datetime.now(tz=datetime.UTC)
        self.solved_tasks[task.task_id] = solve_time
        task.pwned_by[self.user_id] = solve_time
        await self.update(Set({f"solved_tasks.{task.task_id}": solve_time}))
        await task.update(Set({f"pwned_by.{self.user_id}": solve_time}))

        # get previous score and sum it to solver score
        prev_score = task.scoring.points
        self.score += prev_score

        # if do_recalc, recalc all the scoreboard... only users, who solved task
        do_recalc = task.scoring.solve_task()
        await task.update(
            Set(
                {str(TaskDB.scoring): task.scoring},
            ),
            # bulk_writer=bw,
        )

        if do_recalc:
            new_score = task.scoring.points
            diff = prev_score - new_score
            logger.info(f"Solve task: {task.short_desc()}, oldscore={prev_score}, newscore={new_score}, diff={diff}")

            for solver_id in task.pwned_by:
                if solver_id == self.user_id:
                    self.score -= diff
                    continue

                solver = await UserDB.find_by_user_uuid(solver_id)
                if not solver:
                    logger.warning(f"WTF: {solver_id}, {task.short_desc()}, {solver = }")
                    continue

                solver.score -= diff
                await solver.update(
                    Set({UserDB.score: self.score}),
                    bulk_writer=bw,
                )

        await self.update(
            Set({UserDB.score: self.score}),
            bulk_writer=bw,
        )

        return task.task_id

    @classmethod
    async def recalc_scoreboard(cls: type[Self]) -> None:
        # WTF: db_lock?
        task_cache = await TaskDB.get_all()

        async with BulkWriter() as bw:
            for user in (await cls.get_all()).values():
                await user.recalc_score(task_cache, bw=bw)

            logger.info(bw.operations)

    @classmethod
    async def populate(cls: type[Self], model: auth.AuthBase.AuthModel) -> Self:
        user = cls(auth_source=model)
        await user.insert()  # type: ignore # WTF: bad library
        return user

    @classmethod
    async def find_by_user_uuid(cls: type[Self], user_id: uuid.UUID) -> Self | None:
        return await cls.find_one(cls.user_id == user_id)

    @classmethod
    async def find_by_username(cls: type[Self], username: str) -> Self | None:
        return await cls.find_one(cls.username == username)

    @classmethod
    async def get_all(cls: type[Self]) -> dict[uuid.UUID, Self]:
        return {i.user_id: i for i in await cls.find_all().to_list()}

    @classmethod
    async def get_all_projected(cls: type[Self], projection: type[_TT]) -> dict[uuid.UUID, _TT]:
        return {i.user_id: i for i in await cls.find_all().project(projection).to_list()}  # type: ignore # FIXME: fix.

    @classmethod
    async def get_user_uniq_field(
        cls: type[Self],
        base: type[auth.AuthBase.AuthModel],
        field: Hashable,
    ) -> Self | None:
        x = _And(
            cls.auth_source.classtype == base.get_classtype(),
            {f"auth_source.{base.get_uniq_field_name()}": field},
        )
        return await cls.find_one(x)

    class Settings:
        name: ClassVar = "users"
        indexes: ClassVar = [
            [
                ("user_id", pymongo.ASCENDING),
            ],
        ]


class DBClient:
    client: AsyncIOMotorClient  # type: ignore # bad library ;(
    db: AsyncIOMotorDatabase  # type: ignore # bad library ;(

    def __init__(self) -> None:
        pass

    async def init(self) -> None:
        self.client = AsyncIOMotorClient(str(settings.MONGO), tz_aware=True)
        self.db = self.client[settings.DB_NAME]
        await init_beanie(database=self.db, document_models=[TaskDB, UserDB])  # type: ignore # bad library ;(
        logger.info("Beanie init ok")

    async def close(self) -> None:
        logger.info("DB close ok")

    async def reset_db(self) -> None:
        if not settings.DEBUG:
            logger.warning("DB Reset without debug")
            return

        await self.client.drop_database(settings.DB_NAME)


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
