import typing
import uuid
from types import TracebackType

import httpx

from .. import app, auth, config, schema
from .base import settings
from .models import AllTasks, AllUsers, RawTask, RawUser, UserPrivate, UserPublic


class YATB:
    s: httpx.AsyncClient

    def __init__(self) -> None:
        self.s = httpx.AsyncClient(base_url=settings.base_url)

    def set_admin_token(self, token: str = config.settings.API_TOKEN) -> None:
        self.s.headers["X-Token"] = token

    def make_user_token(self, user: schema.User) -> str:
        return f"Bearer {auth.create_user_token(user)}"

    async def register_user(self, user: RawUser) -> UserPrivate:
        resp = await self.s.post(
            app.url_path_for("api_auth_simple_register"),
            json=schema.SimpleAuth.Form._Internal(
                username=user.username,
                password=user.password,
            ).model_dump(mode="json"),
        )
        resp.raise_for_status()

        ret = await self.find_user_by_name(user.username)
        if not ret:
            raise Exception("WTF")
        return ret

    async def get_self(self) -> UserPublic:
        return UserPublic.model_validate((await self.s.get(app.url_path_for("api_users_me"))).json())

    async def get_all_tasks(self) -> dict[uuid.UUID, schema.Task]:
        resp = AllTasks.model_validate((await self.s.get(app.url_path_for("api_admin_tasks"))).json())
        return resp.root

    async def get_all_users(self) -> dict[uuid.UUID, UserPrivate]:
        resp = AllUsers.model_validate((await self.s.get(app.url_path_for("api_admin_users"))).json())
        return resp.root

    async def assign_task_to_user(self, user_id: uuid.UUID, task_id: uuid.UUID) -> UserPrivate:
        resp = await self.s.post(
            app.url_path_for("api_admin_assign_task_to_user", user_id=user_id),
            params={"task_id": str(task_id)},
        )
        return UserPrivate.model_validate(resp.json())

    async def deassign_task_to_user(self, user_id: uuid.UUID, task_id: uuid.UUID) -> UserPrivate:
        resp = await self.s.post(
            app.url_path_for("api_admin_deassign_task_to_user", user_id=user_id),
            params={"task_id": str(task_id)},
        )
        return UserPrivate.model_validate(resp.json())

    async def detele_everything_but_tasks(self):
        resp = await self.s.delete(app.url_path_for("api_detele_everything_but_tasks"))
        resp.raise_for_status()

    async def detele_everything(self):
        resp = await self.s.delete(app.url_path_for("api_detele_everything"))
        resp.raise_for_status()

    async def find_user_by_name(self, username: str) -> UserPrivate | None:
        users = await self.get_all_users()
        for user in users.values():
            if user.username == username:
                return user

        return None

    async def find_task_by_name(self, task_name: str) -> schema.Task | None:
        tasks = await self.get_all_tasks()
        for task in tasks.values():
            if task.task_name == task_name:
                return task

        return None

    async def create_task(self, task: RawTask) -> schema.Task:
        new_task = (
            await self.s.post(
                app.url_path_for("api_admin_task_create"),
                json=schema.TaskForm(
                    task_name=task.task_name,
                    description=task.description,
                    category=task.category,
                    flag=schema.flags.StaticFlag(flag=task.flag, flag_base=settings.flag_base),
                    scoring=schema.scoring.DynamicKKSScoring(),
                    author=task.author,
                ).model_dump(mode="json"),
            )
        ).json()
        return schema.Task.model_validate(new_task)

    async def admin_recalc_scoreboard(self) -> None:
        resp = await self.s.get(app.url_path_for("api_admin_recalc_scoreboard"))
        resp.raise_for_status()

    async def admin_recalc_tasks(self) -> None:
        resp = await self.s.get(app.url_path_for("api_admin_recalc_tasks"))
        resp.raise_for_status()

    async def update_task(self, task: schema.Task) -> schema.Task:
        new_task = (
            await self.s.post(
                app.url_path_for("api_admin_task_edit", task_id=task.task_id),
                json=task.model_dump(mode="json"),
            )
        ).json()
        return schema.Task.model_validate(new_task)

    async def solve_as_user(self, user: schema.User, flag: str) -> str:
        token = self.make_user_token(user)
        resp = await self.s.post(
            app.url_path_for("api_task_submit_flag"),
            json=schema.FlagForm(flag=flag).model_dump(mode="json"),
            headers={"X-Auth-Token": token},
        )
        resp.raise_for_status()
        return resp.text

    async def __aenter__(self):
        self.s = await self.s.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self.s.__aexit__(exc_type=exc_type, exc_value=exc_value, traceback=traceback)  # type: ignore
