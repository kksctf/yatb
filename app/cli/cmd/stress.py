import asyncio

import httpx

from ..base import tapp


@tapp.command()
def make_load(url: str):
    async def _a():
        async with httpx.AsyncClient() as c:

            async def task():
                print("Start")
                for _ in range(0, 1000):
                    r = await c.get(url)
                    _ = r.text
                print("End")

            async with asyncio.TaskGroup() as tg:
                for _ in range(0, 10):
                    tg.create_task(task())

    asyncio.run(_a())
