import typing
import uuid
from types import TracebackType

import httpx

# from dtc.config import settings as dtc_settings
from yatb import auth, schema
from yatb.app import app
from yatb.config import settings as yatb_settings
from yatb.shared.s3.client import MinioEx

from .base import settings
from .models import AllTasks, AllUsers


class YATB:
    s: httpx.AsyncClient
    s3: MinioEx

    def __init__(self, *, set_default_token: bool = True) -> None:
        self.s = httpx.AsyncClient(base_url=settings.UPSTREAM)

        if set_default_token:
            self.set_admin_token(yatb_settings.API_TOKEN)

        # self.s3 = MinioEx(
        #     endpoint=dtc_settings.s3_endpoint,
        #     access_key=dtc_settings.S3_ACCESS,
        #     secret_key=dtc_settings.S3_SECRET,
        #     secure=False,  # http for False, https for True
        # )

    async def setup_s3(self) -> None:
        await self.s3.setup_buckets(
            [
                # dtc_settings.STATIC_BUCKET_NAME,
                # dtc_settings.TASKS_BUCKET_NAME,
                # dtc_settings.BUILD_RESULT_BUCKET_NAME,
            ],
        )

    def set_admin_token(self, token: str = yatb_settings.API_TOKEN) -> None:
        self.s.headers["X-Token"] = token

    def make_user_token(self, user: schema.User) -> str:
        return f"Bearer {auth.create_user_token(user)}"

    # async def register_user(self, user: RawUser) -> UserPrivate:
    #     resp = await self.s.post(
    #         app.url_path_for("api_auth_simple_register"),
    #         json=schema.SimpleAuth.Form._Internal(
    #             username=user.username,
    #             password=user.password,
    #         ).model_dump(mode="json"),
    #     )
    #     resp.raise_for_status()

    #     ret = await self.find_user_by_name(user.username)
    #     if not ret:
    #         raise Exception("WTF")
    #     return ret

    async def get_self(self) -> schema.User:
        return schema.User.public_model.model_validate((await self.s.get(app.url_path_for("api_users_me"))).json())

    async def get_all_tasks(self) -> dict[uuid.UUID, schema.Task]:
        resp = AllTasks.model_validate((await self.s.get(app.url_path_for("api_admin_tasks"))).json())
        return resp.root

    async def get_all_users(self) -> dict[uuid.UUID, schema.User]:
        resp = AllUsers.model_validate((await self.s.get(app.url_path_for("api_admin_users"))).json())
        return resp.root

    async def assign_task_to_user(self, user_id: uuid.UUID, task_id: uuid.UUID) -> schema.User:
        resp = await self.s.post(
            app.url_path_for("api_admin_assign_task_to_user", user_id=user_id),
            params={"task_id": str(task_id)},
        )
        return schema.User.admin_model.model_validate(resp.json())

    async def deassign_task_to_user(self, user_id: uuid.UUID, task_id: uuid.UUID) -> schema.User:
        resp = await self.s.post(
            app.url_path_for("api_admin_deassign_task_to_user", user_id=user_id),
            params={"task_id": str(task_id)},
        )
        return schema.User.admin_model.model_validate(resp.json())

    async def detele_everything_but_tasks(self):
        resp = await self.s.delete(app.url_path_for("api_detele_everything_but_tasks"))
        resp.raise_for_status()

    async def detele_everything(self):
        resp = await self.s.delete(app.url_path_for("api_detele_everything"))
        resp.raise_for_status()

    async def find_user_by_name(self, username: str) -> schema.User | None:
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

    async def create_task(self, task: schema.TaskForm) -> schema.Task:
        new_task = (
            await self.s.post(
                app.url_path_for("api_admin_task_create"),
                json=task.model_dump(mode="json"),
            )
        ).json()
        return schema.Task.model_validate(new_task)

    async def create_task_full_form(self, task: schema.TaskForm) -> schema.Task:
        new_task = (
            await self.s.post(
                app.url_path_for("api_admin_task_create"),
                json=task.model_dump(mode="json"),
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
        return schema.Task.admin_model.model_validate(new_task)

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
        await self.setup_s3()
        return self

    async def __aexit__(
        self,
        exc_type: typing.Type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self.s.__aexit__(exc_type=exc_type, exc_value=exc_value, traceback=traceback)  # type: ignore
