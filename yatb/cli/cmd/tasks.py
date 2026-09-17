from collections.abc import Sequence
from io import SEEK_END
from pathlib import Path
from urllib.parse import quote

from pydantic import HttpUrl

from yatb.cli.base import app, c, settings
from yatb.cli.client import YATB
from yatb.cli.models import FileTask, State
from yatb.dtc.connectors.compose import load_compose
from yatb.s3.config import settings as s3_settings
from yatb.yatb.schema import DynamicTaskFeatures, Task, TaskID
from yatb.yatb.schema.attachments import FileAttachment

_TASKS_ARHIVE_LIMIT: int = 2


async def _upload_task(
    *,
    y: YATB,
    state: State,
    tasks_cache: dict[TaskID, Task],
    task_src: Path,
    req_tasks: Sequence[TaskID] = [],
) -> Task | None:
    try:
        task_info: FileTask = FileTask.load_yaml(task_src / "task.yaml")
    except Exception as ex:
        c.print(f"ERROR!!! {task_src = } has bad yaml: {ex!r}")
        return None

    # хотим получить ID таска
    # если таска нет в локальном стейте (значит мы его ещё не заливали - а если и заливали, то никак не сможем его найти)
    # ИЛИ
    # таска нет на проде
    if not (task_id := task_info.id) or task_id not in tasks_cache:
        created_task = await y.create_task_full_form(
            task_info.get_form(req_tasks=req_tasks),
        )
        tasks_cache[created_task.task_id] = created_task

        task_info.id = created_task.task_id
        task_info.save_yaml_to_file()

        c.print(f"Created task: {created_task}\n")

    created_task = tasks_cache[task_info.id]
    c.print(f"Found task: {created_task.task_name!r}")

    created_task.task_name = task_info.name
    created_task.category = task_info.category
    created_task.scoring = task_info.get_scoring()
    created_task.description = task_info.get_description()
    created_task.flag = task_info.get_flag()
    created_task.author = task_info.author
    created_task.dti = task_info.get_dti()
    created_task.req_tasks = list(req_tasks)
    created_task.hidden = task_info.hidden
    created_task.attachments = list(task_info.attachments)

    if created_task.dti:
        deploy_dir = task_src / "deploy"
        if deploy_dir.exists() and (files := list(deploy_dir.iterdir())):
            try:
                load_compose(deploy_dir)
            except Exception as ex:
                c.print(f"ERR: task {task_info.name!r} has invalid compose!")

            path = f"{created_task.task_id}/deploy.tar.gz"
            hash_digest = await y.s3.upload_directory(
                deploy_dir,
                s3_settings.TASKS_BUCKET_NAME,
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
                s3_settings.TASKS_BUCKET_NAME,
                path,
            )
            created_task.dti.builder_info = (path, hash_digest)
        elif not dev_dir.exists() and DynamicTaskFeatures.BUILDER in task_info.full_features:
            c.print(f"ERR: task {task_info.name!r} as service without building data")
        elif not dev_dir.exists() and DynamicTaskFeatures.VM in task_info.full_features:
            c.print(f"ERR: task {task_info.name!r} as vm without customization data")

    public_dir = task_src / "public"
    if public_dir.exists() and (files := sorted(public_dir.iterdir())):
        public_url = f"{settings.PUBLIC_FILES_DOMAIN.rstrip('/')}/shared/{created_task.task_id}"

        if len(files) > _TASKS_ARHIVE_LIMIT or any(file.is_dir() for file in files):
            archive_name = "files.tar.gz"
            object_name = f"{created_task.task_id}/{archive_name}"
            hash_digest = await y.s3.upload_directory(
                public_dir,
                s3_settings.STATIC_BUCKET_NAME,
                object_name,
                ignore_cache=False,
            )
            archive = await y.s3.stat_object(s3_settings.STATIC_BUCKET_NAME, object_name)
            size_bytes = archive.size
            if size_bytes is None:
                raise ValueError(f"S3 did not return a size for {object_name}")
            created_task.attachments.append(
                FileAttachment(
                    name=archive_name,
                    url=HttpUrl(f"{public_url}/{archive_name}"),
                    size_bytes=size_bytes,
                    sha256=hash_digest,
                ),
            )
            c.print(f"[+] '{created_task.task_name}': uploaded archive from {public_dir!r}")
        else:
            for file in files:
                with file.open("rb") as f:
                    hash_digest = await y.s3.intelligent_put_object(
                        f,
                        s3_settings.STATIC_BUCKET_NAME,
                        f"{created_task.task_id}/{file.name}",
                    )
                    size_bytes = f.seek(0, SEEK_END)
                created_task.attachments.append(
                    FileAttachment(
                        name=file.name,
                        url=HttpUrl(f"{public_url}/{quote(file.name, safe='')}"),
                        size_bytes=size_bytes,
                        sha256=hash_digest,
                    ),
                )
                c.print(f"[+] '{created_task.task_name}': uploaded file {file}")

    created_task = await y.update_task(task=created_task)

    task_info.save_yaml_to_file()

    c.print(f"Updated task: {created_task.task_name!r}")
    return created_task


# @app.command()
# async def upload_task(
#     task_dir: Path,
#     *,
#     drop: bool = False,
#     state_path: Path = Path() / "yatb_state.json",
# ) -> None:
#     task_dir = task_dir.expanduser().resolve()

#     async with State.get(state_path) as state, YATB() as y:
#         y.set_admin_token()

#         task_to_uuid_copy = {}
#         if drop:
#             await y.detele_everything()

#             task_to_uuid_copy = state.task_to_uuid.copy()
#             state.task_to_uuid.clear()

#         tasks_cache: dict[UUID, Task] = await y.get_all_tasks()
#         c.print(f"Found {len(tasks_cache)} tasks on live instance")

#         await _upload_task(
#             y=y,
#             state=state,
#             tasks_cache=tasks_cache,
#             task_src=task_dir,
#         )


async def sync_tasks(
    y: YATB,
    state: State,
    main_tasks_dir: Path,
    *,
    delete_orphane: bool = True,
):
    tasks_cache: dict[TaskID, Task] = await y.get_all_tasks()
    c.print(f"Running in live mode, found {len(tasks_cache)} tasks")

    touched_tasks: set[TaskID] = set()
    for task_yaml in main_tasks_dir.rglob("task.yaml"):
        if task_yaml.is_dir() or task_yaml.parent.name.startswith("."):
            c.print(f"Werid {task_yaml = }")
            continue

        task_src = task_yaml.parent

        try:
            task = await _upload_task(
                y=y,
                state=state,
                tasks_cache=tasks_cache,
                task_src=task_src,
                req_tasks=[],
            )
            touched_tasks.add(task.task_id)  # pyright: ignore[reportOptionalMemberAccess] # TODO: WTF
        except Exception as ex:
            c.print(f"Got error {ex = } uploading {task_src = }")
            raise

    for tid in set(tasks_cache.keys()) - touched_tasks:
        task = tasks_cache[tid]
        c.print(
            f"Found orphaned task: {tid} -> "  # ...
            f"{task.task_name = }, {task.pwned_by = }",
        )
        if delete_orphane:
            await y.delete_task(tid)


@app.command()
async def upload_tasks(
    main_tasks_dir: Path,
    *,
    drop: bool = False,
    # live: bool = True,
    state_path: Path = Path() / "yatb_state.json",
):
    main_tasks_dir = main_tasks_dir.expanduser().resolve()

    async with State.get(state_path, main_tasks_dir) as state, YATB() as y:
        y.set_admin_token()

        if drop:
            await y.detele_everything()
