import asyncio
import uuid

import typer

from ... import config
from ...schema.task import Task

#
from ..base import c, tapp
from ..client import YATB
from ..models import RawTask

#
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
            y.set_admin_token()
            await y.detele_everything()

    asyncio.run(_a())


@tapp.command()
def recalc():
    async def _a():
        async with YATB() as y:
            y.set_admin_token()
            await y.admin_recalc_scoreboard()

    asyncio.run(_a())


# @tapp.command()
# def cmd():  # noqa: CCR001,ANN201
#     async def _a():
#         async with YATB() as y:
#             y.set_admin_token(config.settings.API_TOKEN)

#     asyncio.run(_a())
