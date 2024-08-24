import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

from pydantic_yaml import parse_yaml_raw_as

from ... import schema
from ...schema.task import DynamicTaskInfo, DynamicTaskType, Task, TaskForm
from ..base import c, settings, tapp
from ..client import YATB
from ..models import FileTask, RawTask, State


def task_to_raw(task: FileTask) -> TaskForm:
    name = task.full_name
    description = task.description.strip().strip('"').strip("'")

    flag = task.flag
    if flag.startswith(settings.flag_base + "{") and flag.endswith("}"):
        flag = flag.removeprefix(settings.flag_base + "{")
        flag = flag.removesuffix("}")

    return TaskForm(
        task_name=name,
        category=task.category,
        description=description,
        author=task.author,
        dynamic_task_info=DynamicTaskInfo(
            dynamic_task_type=DynamicTaskType.SERVICE,  # TODO: builder
        ),
        flag=schema.flags.DynamicKKSFlag(dynamic_flag_base=flag, flag_base=settings.flag_base),
        scoring=schema.scoring.DynamicKKSScoring(),
    )


@tapp.command()
def prepare_tasks(
    main_tasks_dir: Path,
    # static_files_dir: Path,
    # deploy_files_dir: Path,
    *,
    drop: bool = False,
    # live: bool = True,
    state_path: Path = Path() / "yatb_state.json",
):
    state = State.model_validate_json(state_path.read_text()) if state_path.exists() else State()

    main_tasks_dir = main_tasks_dir.expanduser().resolve()

    async def _a():
        async with YATB() as y:
            y.set_admin_token()

            if drop:
                await y.detele_everything()
                state.task_to_uuid.clear()

            tasks_cache: dict[UUID, Task] = await y.get_all_tasks()
            c.print(f"Running in live mode, found {len(tasks_cache)} tasks")

            for category_src in main_tasks_dir.iterdir():
                if not category_src.is_dir():
                    continue

                for task_src in category_src.iterdir():
                    if not task_src.is_dir():
                        continue

                    if not (task_src / "task.yaml").exists():
                        continue

                    try:
                        task_info = parse_yaml_raw_as(FileTask, (task_src / "task.yaml").read_text())
                    except Exception as ex:
                        c.print(f"ERROR!!! {task_src = } has bad yaml: {ex!r}")
                        continue

                    if task_src not in state.task_to_uuid:
                        created_task = await y.create_task_full_form(task_to_raw(task_info))
                        tasks_cache[created_task.task_id] = created_task
                        state.task_to_uuid[task_src] = created_task.task_id
                        c.print(f"Created task: {created_task}")
                        continue

                    created_task = tasks_cache[state.task_to_uuid[task_src]]
                    c.print(f"Found task: {created_task}")

        to_env = {str(uuid): str((path / "deploy").resolve()) for path, uuid in state.task_to_uuid.items()}
        c.print(json.dumps(to_env, indent=4))

    try:
        asyncio.run(_a())
    finally:
        state_path.write_text(state.model_dump_json(indent=4))
