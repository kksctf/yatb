import datetime
from collections.abc import Hashable, Iterable, Mapping, Sequence
from typing import ClassVar, Literal, Self

import pymongo
from beanie import BulkWriter
from beanie.operators import And as _And
from beanie.operators import Set
from pydantic import BaseModel

from yatb.config import settings
from yatb.schema import Task, TaskID, User, UserID, auth
from yatb.utils.log_helper import get_logger

from .base import DocumentEx
from .task import TaskDB

logger = get_logger("db.task")


class UserDB(DocumentEx[User], User):
    class ScoreboardProjection(BaseModel):
        user_id: UserID
        username: str
        score: int
        solved_tasks: dict[TaskID, datetime.datetime]
        is_admin: bool  # TODO: wtf with rights and fields

        def get_last_solve_time(self) -> tuple[TaskID, datetime.datetime] | tuple[Literal[""], datetime.datetime]:
            if len(self.solved_tasks) > 0:
                return max(self.solved_tasks.items(), key=lambda x: x[1])

            return ("", datetime.datetime.fromtimestamp(0, tz=datetime.UTC))

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
        await user.insert()
        return user

    @classmethod
    async def find_by_user_uuid(cls: type[Self], user_id: UserID) -> Self | None:
        return await cls.find_one(cls.user_id == user_id)

    @classmethod
    async def find_by_username(cls: type[Self], username: str) -> Self | None:
        return await cls.find_one(cls.username == username)

    @classmethod
    async def get_all(cls: type[Self]) -> dict[UserID, Self]:
        return {i.user_id: i for i in await cls.find_all().to_list()}

    @classmethod
    async def get_all_projected[T: BaseModel](cls: type[Self], projection: type[T]) -> dict[UserID, T]:
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

    @classmethod
    def filter_scoreboard[T: User | UserDB.ScoreboardProjection](cls, users: Iterable[T]) -> Sequence[T]:
        ret = users

        if not settings.DEBUG:
            ret = filter(lambda x: not x.is_admin, ret)

        ret = sorted(
            ret,
            key=lambda i: (
                -i.score,
                i.get_last_solve_time()[1],
            ),
            reverse=False,
        )

        return ret

    @classmethod
    async def get_filtered_scoreboard(cls) -> Sequence[Self]:
        users = await cls.get_all()

        return cls.filter_scoreboard(users.values())

    @classmethod
    async def get_filtered_projected_scoreboard(cls) -> Sequence[ScoreboardProjection]:
        users = await cls.get_all_projected(UserDB.ScoreboardProjection)

        return cls.filter_scoreboard(users.values())

    async def recalc_score_one(self) -> None:
        # WTF: db_lock?
        task_cache = await TaskDB.get_all()

        async with BulkWriter() as bw:
            await self.recalc_score(task_cache, bw=bw)
            logger.info(bw.operations)

    async def recalc_score(self, _task_cache: Mapping[TaskID, Task | None], bw: BulkWriter) -> None:
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
            # update score, if it changed
            await self.update(Set({UserDB.score: self.score}), bulk_writer=bw)

    async def solve_task_bw(self, task: TaskDB) -> TaskID:
        async with BulkWriter() as bw:
            ret = await self.solve_task(task, bw=bw)
            logger.info(bw.operations)

        return ret

    async def solve_task(self, task: TaskDB, bw: BulkWriter) -> TaskID:
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
                    Set({UserDB.score: solver.score}),
                    bulk_writer=bw,
                )

        await self.update(
            Set({UserDB.score: self.score}),
            bulk_writer=bw,
        )

        return task.task_id

    class Settings:
        name: ClassVar = "users"
        indexes: ClassVar = [
            [
                ("user_id", pymongo.ASCENDING),
            ],
        ]
