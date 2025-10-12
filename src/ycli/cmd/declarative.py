from pathlib import Path
from uuid import uuid4

from yatb import schema
from ycli.base import app, c
from ycli.client import YATB
from ycli.cmd.tasks import sync_tasks
from ycli.models import State


@app.command()
async def sync(
    target: Path,
    *,
    drop: bool = False,
    # live: bool = True,
    state_path: Path = Path() / "yatb_state.json",
) -> None:
    target = target.expanduser().resolve()

    async with State.get(state_path, target) as state, YATB() as y:
        y.set_admin_token()

        if drop:
            await y.detele_everything()

        await sync_tasks(y, state, target / "tasks")
