import io
import shutil
import subprocess
from pathlib import Path
from typing import Sequence
from uuid import UUID

from pydantic_yaml import parse_yaml_raw_as

from dtc.config import settings as dtc_settings
from yatb.schema import DynamicTaskFeatures
from yatb.schema.task import Task
from ycli.base import app, c, settings
from ycli.client import YATB
from ycli.models import FileTask, State

_TASKS_ARHIVE_LIMIT: int = 2


async def _upload_task(
    *,
    y: YATB,
    state: State,
    task_to_uuid_copy: dict[Path, UUID] | None,
    tasks_cache: dict[UUID, Task],
    task_src: Path,
    req_tasks: Sequence[UUID] = [],
) -> Task | None:
    try:
        task_info: FileTask = parse_yaml_raw_as(FileTask, (task_src / "task.yaml").read_text())
    except Exception as ex:
        c.print(f"ERROR!!! {task_src = } has bad yaml: {ex!r}")
        return

    if task_src not in state.task_to_uuid or state.task_to_uuid[task_src] not in tasks_cache:
        # WTF: что тут происходит......
        if task_to_uuid_copy and task_src in task_to_uuid_copy:
            old_task_uuid = task_to_uuid_copy[task_src]
        elif task_src in state.task_to_uuid and state.task_to_uuid[task_src] not in tasks_cache:
            old_task_uuid = state.task_to_uuid[task_src]
        else:
            old_task_uuid = None

        created_task = await y.create_task_full_form(
            task_info.get_form(
                old_task_uuid=old_task_uuid,
                req_tasks=req_tasks,
            ),
        )
        tasks_cache[created_task.task_id] = created_task
        state.task_to_uuid[task_src] = created_task.task_id
        c.print(f"Created task: {created_task}\n")

    created_task = tasks_cache[state.task_to_uuid[task_src]]
    c.print(f"Found task: {created_task}\n")

    created_task.task_name = task_info.name
    created_task.description = task_info.description
    created_task.flag = task_info.get_flag()
    created_task.hidden = task_info.hidden

    if created_task.dti:
        deploy_dir = task_src / "deploy"
        if deploy_dir.exists() and (files := list(deploy_dir.iterdir())):
            path = f"{created_task.task_id}/deploy.tar.gz"
            hash_digest = await y.s3.upload_directory(
                deploy_dir,
                dtc_settings.TASKS_BUCKET_NAME,
                path,
            )
            created_task.dti.service_info = (path, hash_digest)
        elif not deploy_dir.exists() and DynamicTaskFeatures.SERVICE in task_info.full_features:
            c.print(f"ERR: task {task_info.name!r} as service without building data")

        dev_dir = task_src / "dev"
        if dev_dir.exists() and (files := list(dev_dir.iterdir())):
            path = f"{created_task.task_id}/dev.tar.gz"
            hash_digest = await y.s3.upload_directory(
                dev_dir,
                dtc_settings.TASKS_BUCKET_NAME,
                path,
            )
            created_task.dti.builder_info = (path, hash_digest)
        elif not dev_dir.exists() and DynamicTaskFeatures.BUILDER in task_info.full_features:
            c.print(f"ERR: task {task_info.name!r} as service without building data")
        elif not dev_dir.exists() and DynamicTaskFeatures.VM in task_info.full_features:
            c.print(f"ERR: task {task_info.name!r} as vm without customization data")

    public_dir = task_src / "public"
    if public_dir.exists() and (files := list(public_dir.iterdir())):
        files_hash = subprocess.check_output(  # noqa: ASYNC221, S603
            "find ./public -type f -exec sha256sum {} \\;",  # noqa: S607
            shell=True,
            cwd=task_src,
            stderr=subprocess.STDOUT,
        )

        created_task.description += "\n\n---\n\n"
        created_task.description += '<div class="card-text row d-flex justify-content-between">'

        if len(files) > _TASKS_ARHIVE_LIMIT:
            archive_name = "files.tag.gz"
            created_task.description += (
                "<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
                f"href='{settings.PUBLIC_FILES_DOMAIN}/shared/{created_task.task_id}/{archive_name}' "
                f"rel='noopener noreferrer' target='_blank'>{archive_name}</a>\n"
            )
            await y.s3.upload_directory(
                public_dir,
                dtc_settings.TASKS_BUCKET_NAME,
                f"{created_task.task_id}/{archive_name}",
            )
            c.print(f"\t\t[+] '{created_task.task_name}': uploaded archive ({len(files) = } > 2) from {public_dir!r}")
        else:
            for file in files:
                created_task.description += (
                    "<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
                    f"href='{settings.PUBLIC_FILES_DOMAIN}/shared/{created_task.task_id}/{file.name}' "
                    f"rel='noopener noreferrer' target='_blank'>{file.name}</a>\n"
                )
                with file.open("rb") as f:
                    await y.s3.put_object(
                        dtc_settings.STATIC_BUCKET_NAME,
                        f"{created_task.task_id}/{file.name}",
                        f,
                        length=file.stat().st_size,
                    )
                c.print(f"\t\t[+] '{created_task.task_name}': uploaded file {file}")

        await y.s3.put_object(
            dtc_settings.STATIC_BUCKET_NAME,
            f"{created_task.task_id}/.sha256",
            io.BytesIO(files_hash),
            length=len(files_hash),
        )

        created_task.description += (
            "<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
            f"href='{settings.PUBLIC_FILES_DOMAIN}/shared/{created_task.task_id}/.sha256' rel='noopener noreferrer' "
            "target='_blank'>.sha256</a>\n"
        )

        created_task.description = created_task.description.strip() + "</div>"

    created_task = await y.update_task(task=created_task)
    c.print(f"Updated task: {created_task}")
    return created_task


@app.command()
async def upload_task(
    task_dir: Path,
    *,
    drop: bool = False,
    state_path: Path = Path() / "yatb_state.json",
) -> None:
    task_dir = task_dir.expanduser().resolve()

    async with State.get(state_path) as state, YATB() as y:
        y.set_admin_token()

        task_to_uuid_copy = {}
        if drop:
            await y.detele_everything()

            task_to_uuid_copy = state.task_to_uuid.copy()
            state.task_to_uuid.clear()

        tasks_cache: dict[UUID, Task] = await y.get_all_tasks()
        c.print(f"Found {len(tasks_cache)} tasks on live instance")

        await _upload_task(
            y=y,
            state=state,
            task_to_uuid_copy=task_to_uuid_copy,
            tasks_cache=tasks_cache,
            task_src=task_dir,
        )


@app.command()
async def upload_tasks(
    main_tasks_dir: Path,
    *,
    drop: bool = False,
    # live: bool = True,
    state_path: Path = Path() / "yatb_state.json",
):
    main_tasks_dir = main_tasks_dir.expanduser().resolve()

    async with State.get(state_path) as state, YATB() as y:
        task_to_uuid_copy: dict[Path, UUID] | None = None

        y.set_admin_token()

        if drop:
            await y.detele_everything()

            task_to_uuid_copy = state.task_to_uuid.copy()
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
                    await _upload_task(
                        y=y,
                        state=state,
                        task_to_uuid_copy=task_to_uuid_copy,
                        tasks_cache=tasks_cache,
                        task_src=task_src,
                        req_tasks=[],
                    )
                except Exception as ex:
                    c.print(f"Got error {ex = } uploading {task_src = }")
                    raise
