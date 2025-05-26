import asyncio

import httpx

from ..base import c, tapp
from ..client import YATB
from ..models import RawUser


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
            y.set_admin_token()
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
