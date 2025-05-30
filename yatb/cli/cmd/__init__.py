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
    RawTask(flag="task1", task_name="Warm-up crypto", category="crypto", description="XOR basics"),
    RawTask(flag="task2", task_name="Heap fun", category="binary", description="UAF exploitation"),
    RawTask(flag="task3", task_name="SQLi 101", category="web", description="Classic injection"),
    RawTask(flag="task4", task_name="Forensic trace", category="forensic", description="PCAP puzzle"),
    RawTask(flag="task5", task_name="Obscure stego", category="other", description="Audio LSB"),
    RawTask(flag="task6", task_name="RSA baby", category="crypto", description="e=3 low exponent"),
    RawTask(flag="task7", task_name="Fmt-str 101", category="binary", description="Leak & write"),
    RawTask(flag="task8", task_name="XSS everywhere", category="web", description="DOM clobbering"),
    RawTask(flag="task9", task_name="Memory dump", category="forensic", description="WinDbg basics"),
    RawTask(
        flag="task10",
        task_name="Regex confusion",
        category="other",
        description="Catastrophic backtracking",
    ),
    RawTask(flag="task11", task_name="CBC bit-flip", category="crypto", description="Padding oracle"),
    RawTask(flag="task12", task_name="ROP chain", category="binary", description="ret2libc → system"),
    RawTask(flag="task13", task_name="Race condition", category="web", description="Flask session fix"),
    RawTask(flag="task14", task_name="ELF timeline", category="forensic", description="Shell history"),
    RawTask(flag="task15", task_name="Brainf**k encode", category="other", description="Esoteric encoding"),
    RawTask(flag="task16", task_name="Elliptic twist", category="crypto", description="Curve math"),
    RawTask(flag="task17", task_name="Sigreturn-oriented", category="binary", description="SROP primer"),
    RawTask(flag="task18", task_name="SSRF to RCE", category="web", description="Metadata abuse"),
    RawTask(flag="task19", task_name="Malware config", category="forensic", description="C2 extractor"),
    RawTask(flag="task20", task_name="Reverse Polish", category="other", description="Obfuscated calc"),
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

            await y.admin_recalc_tasks()
            await y.admin_recalc_scoreboard()

    asyncio.run(_a())


@tapp.command()
def unhide():
    async def _a():
        async with YATB() as y:
            y.set_admin_token()

            async with asyncio.TaskGroup() as tg:
                for task in (await y.get_all_tasks()).values():
                    task.hidden = False
                    tg.create_task(y.update_task(task))

    asyncio.run(_a())


# @tapp.command()
# def cmd():  # noqa: CCR001,ANN201
#     async def _a():
#         async with YATB() as y:
#             y.set_admin_token(config.settings.API_TOKEN)

#     asyncio.run(_a())
