"""The admin-only task debug block, served as its own htmx fragment.

Rendering this inline used to mean the raw `TaskDB` — flag included — sat in the Jinja
context of every task page, with a single `{% if curr_user.is_admin %}` standing between
a player and the flag. Dropping that one line in a template leaked it. Here the guard is
the `CURR_ADMIN` dependency: a non-admin gets a 403 and htmx swaps nothing, no matter
what the calling template does.

Lives in `view/` rather than next to `api_admin_task_get`, despite the `/api/admin` path:
`app.py` imports `api` before `view`, so reaching for `response_generator` from
`api/admin/` would run `view/__init__.py` against a half-initialised `yatb.api`. Same
shape as `view/admin/ng.py`'s `api_rotuer`.
"""

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from yatb import schema
from yatb.api.admin.admin_tasks import CURR_TASK
from yatb.auth import CURR_ADMIN
from yatb.db import TaskDB

from .util import response_generator

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    # An HTML fragment has no business in the JSON admin API's schema.
    include_in_schema=False,
)


def admin_dump(task: schema.Task) -> str:
    """Admin-level JSON of a task, for the admin-only debug block."""
    # Goes through `admin_model` like the FastUI admin does, so Private fields and the
    # beanie bookkeeping of `TaskDB` stay out of the rendered page.
    return schema.Task.admin_model.model_validate(task.model_dump()).model_dump_json(indent=2)


@router.get("/task/{task_id}/debug")
async def api_admin_task_debug(req: Request, task: CURR_TASK, user: CURR_ADMIN) -> HTMLResponse:
    return await response_generator(
        req,
        "partials/task_debug.jhtml",
        {
            "task": task,
            "tid2name": await TaskDB.get_names_by_ids(task.req_tasks),
            "admin_json": admin_dump(task),
        },
    )
