import asyncio
import shutil
import subprocess
from pathlib import Path

from ..base import c, files_domain, tapp
from ..client import YATB
from ..models import FileTask


@tapp.command()
def prepare_tasks(
    main_tasks_dir: Path = Path("./tasks"),
    static_files_dir: Path = Path("./deploy/static_files"),
):
    main_tasks_dir = main_tasks_dir.expanduser().resolve()
    static_files_dir = static_files_dir.expanduser().resolve()

    async def _a():
        async with YATB() as y:
            y.set_admin_token()

            for category_src in main_tasks_dir.iterdir():
                if not category_src.is_dir():
                    continue

                for task_src in category_src.iterdir():
                    if not task_src.is_dir():
                        continue

                    category_name = task_src.name
                    task_info = FileTask.parse_file(task_src / "task.json")
                    task_desc = (task_src / "desc.md").read_text(encoding="utf-8")

                    created_task = await y.create_task(task_info.get_raw(category_name, task_desc))
                    c.print(f"Created task: {created_task = }")

                    public_dir = task_src / "public"
                    if public_dir.exists():
                        task_files_dir = static_files_dir / str(created_task.task_id)
                        task_files_dir.mkdir(parents=True, exist_ok=True)

                        files = list(public_dir.iterdir())
                        files_hash = subprocess.check_output(
                            "sha256sum -b public/*",
                            shell=True,
                            cwd=task_src,
                            stderr=subprocess.STDOUT,
                        )

                        created_task.description += "\n\n---\n\n"
                        created_task.description += '<div class="card-text row d-flex justify-content-between">'

                        for file in files:
                            created_task.description += (
                                f"<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
                                f"href='{files_domain}/{created_task.task_id}/{file.name}' rel='noopener noreferrer' "
                                f"target='_blank'>{file.name}</a>\n"
                            )
                            shutil.copy2(file, task_files_dir)
                            c.print(f"\t\t[+] '{created_task.task_name}': uploaded file {file}")

                        (task_files_dir / ".sha256").write_bytes(files_hash)
                        created_task.description += (
                            f"<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
                            f"href='{files_domain}/{created_task.task_id}/.sha256' rel='noopener noreferrer' "
                            f"target='_blank'>.sha256</a>\n"
                        )

                        created_task.description = created_task.description.strip() + "</div>"

                        updated_task = await y.update_task(task=created_task)

                        c.print(f"Updated task: {updated_task}")

    asyncio.run(_a())
