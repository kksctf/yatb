import asyncio
from datetime import datetime
import pickle
import random
import shutil
import string
import subprocess
import typing
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

import httpx
import typer
from rich.console import Console

from app import app, config, schema


class UserPublic(schema.EBaseModel):
    user_id: uuid.UUID
    username: str

    score: int
    solved_tasks: dict[uuid.UUID, datetime]


class UserPrivate(UserPublic):
    is_admin: bool


@dataclass
class RawUser:
    username: str
    password: str = "0"

    def generate_password(self):
        self.password = "".join(random.choices(string.ascii_letters, k=16))


@dataclass
class RawTask:
    task_name: str
    category: str
    description: str

    flag: str

    author: str = ""


class FileTask(schema.BaseModel):
    task_name: str
    flag: str
    is_gulag: bool = False

    author: str = "none"
    category: str | None = None

    def get_raw(self, category_name: str, description: str) -> RawTask:
        return RawTask(
            task_name=self.task_name,
            category=self.category or category_name,
            description=description,
            flag=self.flag,
            author=self.author,
        )


files_domain = "http://127.0.0.1:9999"
base_url = "http://127.0.0.1:8000"

tapp = typer.Typer()
c = Console()


class YATB:
    s: httpx.AsyncClient

    def __init__(self) -> None:
        self.s = httpx.AsyncClient(base_url=base_url)

    def set_admin_token(self, token: str) -> None:
        self.s.headers["X-Token"] = token

    async def register_user(self, user: RawUser) -> None:
        resp = await self.s.post(
            app.url_path_for("api_auth_simple_register"),
            json=schema.SimpleAuth.Form._Internal(
                username=user.username,
                password=user.password,
            ).dict(),
        )
        resp.raise_for_status()

    async def get_self(self) -> UserPublic:
        return UserPublic.parse_obj((await self.s.get(app.url_path_for("api_users_me"))).json())

    async def get_all_tasks(self) -> dict[uuid.UUID, schema.Task]:
        class AllTasks(schema.EBaseModel):
            __root__: dict[uuid.UUID, schema.Task]

        resp = AllTasks.parse_obj((await self.s.get(app.url_path_for("api_admin_tasks"))).json())
        return resp.__root__

    async def get_all_users(self) -> dict[uuid.UUID, UserPrivate]:
        class Allusers(schema.EBaseModel):
            __root__: dict[uuid.UUID, UserPrivate]

        resp = Allusers.parse_obj((await self.s.get(app.url_path_for("api_admin_users"))).json())
        return resp.__root__

    async def assign_task_to_user(self, user_id: uuid.UUID, task_id: uuid.UUID) -> UserPrivate:
        resp = await self.s.post(
            app.url_path_for("api_admin_assign_task_to_user", user_id=user_id),
            params={"task_id": str(task_id)},
        )
        return UserPrivate.parse_obj(resp.json())

    async def deassign_task_to_user(self, user_id: uuid.UUID, task_id: uuid.UUID) -> UserPrivate:
        resp = await self.s.post(
            app.url_path_for("api_admin_deassign_task_to_user", user_id=user_id),
            params={"task_id": str(task_id)},
        )
        return UserPrivate.parse_obj(resp.json())

    async def detele_everything_but_tasks(self):
        resp = await self.s.get(app.url_path_for("api_detele_everything_but_tasks"))
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
                    flag=schema.flags.StaticFlag(flag=task.flag, flag_base="Cup"),
                    scoring=schema.scoring.DynamicKKSScoring(),
                    author=task.author,
                ).dict(),
            )
        ).json()
        return schema.Task.parse_obj(new_task)

    async def update_task(self, task: schema.Task) -> schema.Task:
        new_task = (
            await self.s.post(
                app.url_path_for("api_admin_task_edit", task_id=task.task_id),
                data=task.json(),  # httpx shit ;(, sry
            )
        ).json()
        return schema.Task.parse_obj(new_task)

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


tasks_to_create: list[RawTask] = [
    RawTask(
        task_name="test_task_1",
        category="web",
        description="flag - A\n",
        flag="A",
    ),
    RawTask(
        task_name="test_task_2",
        category="web",
        description="flag - B\n",
        flag="B",
    ),
    RawTask(
        task_name="test_task_3",
        category="web",
        description="flag - C\n",
        flag="C",
    ),
    RawTask(
        task_name="test_task_1_separate",
        category="web",
        description="flag - As\n",
        flag="As",
    ),
    RawTask(
        task_name="test_task_2_separate",
        category="web",
        description="flag - Bs\n",
        flag="Bs",
    ),
    RawTask(
        task_name="test_task_3_separate",
        category="web",
        description="flag - Cs\n",
        flag="Cs",
    ),
]


@tapp.command()
def get_all_tasks():  # noqa: CCR001,ANN201
    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)
            users = await y.get_all_users()
            tasks = await y.get_all_tasks()
            for task in tasks.values():
                c.print(f"{task.task_id = }")
                c.print(f"{task.task_name = }")
                c.print(f"{task.category = }")
                c.print(f"{task.scoring = }")
                c.print(f"{task.flag = }")

                fancy_pwned_by = [f"'{users[user_id].username}'" for user_id in task.pwned_by]
                if fancy_pwned_by:
                    c.print(f"pwned by: {', '.join(fancy_pwned_by)}")

                c.print()

    asyncio.run(_a())


@tapp.command()
def get_all_users():  # noqa: CCR001,ANN201
    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)
            tasks = await y.get_all_tasks()
            users = await y.get_all_users()
            for user in users.values():
                c.print(f"{user.user_id = }")
                c.print(f"{user.username = }")
                c.print(f"{user.is_admin = }")

                fancy_solved = [f"'{tasks[task_id].task_name}'" for task_id in user.solved_tasks]
                if fancy_solved:
                    c.print(f"solved: {', '.join(fancy_solved)}")

                c.print()

    asyncio.run(_a())


@tapp.command()
def drop_users():  # noqa: CCR001,ANN201
    shure = typer.prompt("Are you shure? [y/N]", default="N")
    if shure not in ["y", "yes"]:
        return

    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)
            await y.detele_everything_but_tasks()

    asyncio.run(_a())


@tapp.command()
def init_tasks():
    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)

            for task in tasks_to_create:
                new_task = await y.create_task(task)
                c.log(f"Task created: {new_task = }")

    asyncio.run(_a())


@tapp.command()
def prepare_tasks(
    main_tasks_dir: Path = Path("./tasks"),
    static_files_dir: Path = Path("./deploy/static_files"),
):
    main_tasks_dir = main_tasks_dir.expanduser().resolve()
    static_files_dir = static_files_dir.expanduser().resolve()

    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)

            for category_src in main_tasks_dir.iterdir():
                if not category_src.is_dir():
                    continue

                for task_src in category_src.iterdir():
                    if not task_src.is_dir():
                        continue

                    category_name = task_src.name
                    task_info = FileTask.parse_file(task_src / "task.json")
                    task_desc = (task_src / "desc.md").read_text(encoding="utf-8")

                    created_task = await y.create_task(task_info.get_raw(category_name, task_desc))
                    c.print(f"Created task: {created_task = }")

                    public_dir = task_src / "public"
                    if public_dir.exists():
                        task_files_dir = static_files_dir / str(created_task.task_id)
                        task_files_dir.mkdir(parents=True, exist_ok=True)

                        files = list(public_dir.iterdir())
                        files_hash = subprocess.check_output(
                            "sha256sum -b public/*",
                            shell=True,
                            cwd=task_src,
                            stderr=subprocess.STDOUT,
                        )

                        created_task.description += "\n\n---\n\n"
                        created_task.description += '<div class="card-text row d-flex justify-content-between">'

                        for file in files:
                            created_task.description += (
                                f"<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
                                f"href='{files_domain}/{created_task.task_id}/{file.name}' rel='noopener noreferrer' "
                                f"target='_blank'>{file.name}</a>\n"
                            )
                            shutil.copy2(file, task_files_dir)
                            c.print(f"\t\t[+] '{created_task.task_name}': uploaded file {file}")

                        (task_files_dir / ".sha256").write_bytes(files_hash)
                        created_task.description += (
                            f"<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
                            f"href='{files_domain}/{created_task.task_id}/.sha256' rel='noopener noreferrer' "
                            f"target='_blank'>.sha256</a>\n"
                        )

                        created_task.description = created_task.description.strip() + "</div>"

                        updated_task = await y.update_task(task=created_task)

                        c.print(f"Updated task: {updated_task}")

    asyncio.run(_a())


# @tapp.command()
# def cmd():  # noqa: CCR001,ANN201
#     async def _a():
#         async with YATB() as y:
#             y.set_admin_token(config.settings.API_TOKEN)

#     asyncio.run(_a())


if __name__ == "__main__":
    tapp()
    # asyncio.run(amain())
