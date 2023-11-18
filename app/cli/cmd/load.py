import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

from pydantic_yaml import parse_yaml_raw_as

from ...schema.task import Task
from ..base import c, settings, tapp
from ..client import YATB
from ..models import FileTask


@tapp.command()
def prepare_tasks(
    main_tasks_dir: Path,
    static_files_dir: Path,
    deploy_files_dir: Path,
    *,
    drop: bool = False,
    live: bool = True,
):
    main_tasks_dir = main_tasks_dir.expanduser().resolve()
    static_files_dir = static_files_dir.expanduser().resolve()
    deploy_files_dir = deploy_files_dir.expanduser().resolve()

    async def _a():
        caddy_data = ""
        used_prefix: set[str] = set()

        async with YATB() as y:
            y.set_admin_token()

            if drop:
                if static_files_dir.exists():
                    c.log("Cleaning static files...")
                    shutil.rmtree(static_files_dir)

                if deploy_files_dir.exists():
                    c.log("Cleaning deploy files...")
                    shutil.rmtree(deploy_files_dir)

                await y.detele_everything()

            if live and deploy_files_dir.exists():
                c.log("Cleaning deploy files...")
                shutil.rmtree(deploy_files_dir)

            static_files_dir.mkdir(parents=True, exist_ok=True)
            deploy_files_dir.mkdir(parents=True, exist_ok=True)

            old_tasks: dict[UUID, Task] = {}

            def search_task(target: FileTask) -> Task | None:
                for task in old_tasks.values():
                    if target.full_name == task.task_name:
                        return task
                return None

            if live:
                old_tasks = await y.get_all_tasks()
                c.print(f"Running in live mode, found {len(old_tasks)} tasks")

            for category_src in main_tasks_dir.iterdir():
                if not category_src.is_dir():
                    continue

                for task_src in category_src.iterdir():
                    if not task_src.is_dir():
                        continue

                    if not (task_src / "task.yaml").exists():
                        continue

                    task_info = parse_yaml_raw_as(FileTask, (task_src / "task.yaml").read_text())

                    board_task = search_task(task_info)
                    if live and not board_task:
                        c.print(f"WTF: {task_info = } not found")
                        input("wtf?")

                    created_task = board_task or await y.create_task(task_info.get_raw())
                    c.print(f"Created task: {created_task}")

                    public_dir = task_src / "public"
                    if public_dir.exists() and not live:
                        task_files_dir = static_files_dir / str(created_task.task_id)
                        task_files_dir.mkdir(parents=True, exist_ok=True)

                        files = list(public_dir.iterdir())
                        files_hash = subprocess.check_output(  # noqa: ASYNC101
                            "sha256sum -b public/*",  # noqa: S607
                            shell=True,  # noqa: S602
                            cwd=task_src,
                            stderr=subprocess.STDOUT,
                        )

                        created_task.description += "\n\n---\n\n"
                        created_task.description += '<div class="card-text row d-flex justify-content-between">'

                        for file in files:
                            created_task.description += (
                                f"<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
                                f"href='{settings.files_url}/{created_task.task_id}/{file.name}' rel='noopener noreferrer' "
                                f"target='_blank'>{file.name}</a>\n"
                            )
                            shutil.copy2(file, task_files_dir)
                            c.print(f"\t\t[+] '{created_task.task_name}': uploaded file {file}")

                        (task_files_dir / ".sha256").write_bytes(files_hash)
                        created_task.description += (
                            f"<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
                            f"href='{settings.files_url}/{created_task.task_id}/.sha256' rel='noopener noreferrer' "
                            f"target='_blank'>.sha256</a>\n"
                        )

                        created_task.description = created_task.description.strip() + "</div>"

                        created_task = await y.update_task(task=created_task)

                        c.print(f"Updated task: {created_task}")

                    if (
                        task_info.server_port
                        and task_info.is_http
                        and (prefix := task_info.domain_prefix)
                        and prefix not in used_prefix
                    ):
                        caddy_data += (
                            f"@task-{prefix} host {prefix}.{settings.tasks_domain}\n"
                            f"handle @task-{prefix} {{\n"
                            f"  reverse_proxy 127.0.0.1:{task_info.server_port}\n"
                            "}\n\n"
                        )
                        used_prefix.add(prefix)

                    deploy_dir = task_src / "deploy"
                    if deploy_dir.exists():
                        target_deploy_dir = deploy_files_dir / task_src.name
                        shutil.copytree(deploy_dir, target_deploy_dir)

            c.print("Caddy data:")
            c.print(caddy_data)

    asyncio.run(_a())
