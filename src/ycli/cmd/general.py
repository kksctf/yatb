import asyncio

from rich.prompt import Prompt

from ycli.base import app, c
from ycli.client import YATB


@app.command()
async def drop_users():
    sure = Prompt.ask("Are you sure?", choices=["yes", "no"], default="no", console=c)
    if sure not in ["y", "yes"]:
        return

    async with YATB() as y:
        await y.detele_everything_but_tasks()


@app.command()
async def cleanup():
    async with YATB() as y:
        await y.detele_everything()


@app.command()
async def recalc():
    async with YATB() as y:
        await y.admin_recalc_tasks()
        await y.admin_recalc_scoreboard()


@app.command()
async def unhide():
    async with YATB() as y, asyncio.TaskGroup() as tg:
        for task in (await y.get_all_tasks()).values():
            task.hidden = False
            tg.create_task(y.update_task(task))
