import asyncio

from app import config

from ..base import c, tapp
from ..client import YATB


@tapp.command()
def get_all_tasks():  # noqa: ANN201
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
def get_all_users():  # noqa: ANN201
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
