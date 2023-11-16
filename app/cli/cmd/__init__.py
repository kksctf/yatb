import asyncio
import random
import shutil
import string
import subprocess
import typing
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import TracebackType

import httpx
import typer
from pydantic import BaseModel, RootModel
from rich.console import Console

from app import app, auth, config, schema

from ..base import FLAG_BASE, base_url, c, files_domain, tapp
from ..client import YATB
from ..models import AllTasks, AllUsers, FileTask, RawTask, RawUser, UserPrivate, UserPublic
from . import get as get_cmds
from . import load as load_cmds
from . import stress as stress_cmds

get_cmds = get_cmds
stress_cmds = stress_cmds
load_cmds = load_cmds

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
def drop_users():  # noqa: ANN201
    shure = typer.prompt("Are you shure? [y/N]", default="N")
    if shure not in ["y", "yes"]:
        return

    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)
            await y.detele_everything_but_tasks()

    asyncio.run(_a())


@tapp.command()
def init_tasks():  # noqa: ANN201
    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)

            for task in tasks_to_create:
                new_task = await y.create_task(task)
                c.log(f"Task created: {new_task = }")

    asyncio.run(_a())


@tapp.command()
def cleanup():  # noqa: ANN201
    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)
            await y.detele_everything()

    asyncio.run(_a())


@tapp.command()
def recalc():
    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)
            await y.admin_recalc_scoreboard()

    asyncio.run(_a())


@tapp.command()
def setup_test_env(*, heavy: bool = False):  # noqa: ANN201
    total = 500 if heavy else 6
    lim1 = 200 if heavy else 6
    lim2 = 300 if heavy else 6
    lim3 = 350 if heavy else 6

    users_to_create = [
        RawUser(
            username=f"test_user_{i}",
            password="1",  # noqa: S106
        )
        for i in range(total)
    ]

    async def _a():
        async with YATB() as y:
            y.set_admin_token(config.settings.API_TOKEN)
            await y.detele_everything()

            users = {}

            for task in tasks_to_create:
                new_task = await y.create_task(task)
                new_task.hidden = False
                await y.update_task(new_task)
                c.log(f"Task created: {new_task = }")

            for i, user in enumerate(users_to_create):
                users[i] = await y.register_user(user)

            for i in range(0, lim1, 2):
                await y.solve_as_user(users[i], "A")
                await y.solve_as_user(users[i], "B")

            for i in range(0, lim2, 3):
                await y.solve_as_user(users[i], "B")
                await y.solve_as_user(users[i], "C")

            for i in range(0, lim3, 5):
                await y.solve_as_user(users[i], "As")

    asyncio.run(_a())


# @tapp.command()
# def cmd():  # noqa: CCR001,ANN201
#     async def _a():
#         async with YATB() as y:
#             y.set_admin_token(config.settings.API_TOKEN)

#     asyncio.run(_a())
