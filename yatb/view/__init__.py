import asyncio
import uuid
from collections.abc import Mapping
from pathlib import Path

from fastapi import BackgroundTasks, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute as _APIRoute
from fastapi.routing import APIRouter
from fastapi.templating import Jinja2Templates
from formgen.gen2 import Context as FormContext
from formgen.gen2 import Contexts as FormContexts
from formgen.gen2 import FieldType as FormFieldType
from formgen.gen2 import generate_form
from starlette.routing import Router
from starlette.templating import _TemplateResponse

from fastapi import Query
from fastapi.responses import HTMLResponse

from .. import auth, schema
from ..api import api_tasks, api_users
from ..config import settings
from ..utils.log_helper import get_logger


logger = get_logger("view")

_base_path = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=_base_path / "templates")

router = APIRouter(
    prefix="",
    tags=["view"],
)


def route_generator(req: Request, base_path: str = "/api", *, ignore_admin: bool = True) -> dict[str, str]:
    router: Router = req.scope["router"]
    ret = {}
    for r in router.routes:
        if not isinstance(r, _APIRoute):
            continue
        if not r.path.startswith(base_path):
            continue
        if ignore_admin and r.path.startswith(f"{base_path}/admin"):
            continue

        dummy_params = {i: f"NONE_{i}" for i in set(r.param_convertors.keys())}
        ret[r.name] = str(req.url_for(r.name, **dummy_params))
    return ret


async def response_generator(  # noqa: PLR0913 # impossible to fix
    req: Request,
    filename: str,
    context: dict = {},  # noqa: B006 # iknew.
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    background: BackgroundTasks | None = None,
    *,
    ignore_admin: bool = True,
) -> _TemplateResponse:
    context_base = {
        "request": req,
        "api_list": route_generator(req, ignore_admin=ignore_admin),
    }
    context_base.update(context)
    return await asyncio.get_running_loop().run_in_executor(
        None,
        lambda: templates.TemplateResponse(
            name=filename,
            context=context_base,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        ),
    )


def version_string() -> str:
    return f"kks-tb-{settings.VERSION}"


templates.env.globals["version_string"] = version_string
templates.env.globals["len"] = len
templates.env.globals["template_format_time"] = schema.task.template_format_time
templates.env.globals["set"] = set
templates.env.globals["isinstance"] = isinstance

templates.env.globals["DEBUG"] = settings.DEBUG
templates.env.globals["FLAG_BASE"] = settings.FLAG_BASE
templates.env.globals["CTF_NAME"] = settings.CTF_NAME

templates.env.globals["generate_form"] = generate_form
templates.env.globals["FormFieldType"] = FormFieldType
templates.env.globals["FormContext"] = FormContext
templates.env.globals["FormContexts"] = FormContexts

from . import admin  # noqa

router.include_router(admin.router)


@router.get("/")
@router.get("/index")
async def index(request: Request, user: auth.CURR_USER_SAFE):
    return await response_generator(request, "index.jhtml", {"curr_user": user})


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_get(
    request: Request,
    user: auth.CURR_USER_SAFE,
    category: list[str] | None = Query(None),
):
    tasks = await api_tasks.api_tasks_get(user)

    # collect every user UUID appearing in first/last pwn lists
    uid_set: set[uuid.UUID] = set()
    for t in tasks:
        uid_set.update(t.pwned_by.keys())

    uid2name = {uid: (await api_users.api_users_get(uid, user)).username for uid in uid_set}

    # Detect if this is an HTMX call (partial refresh) or a full-page load
    partial_refresh = request.headers.get("hx-request") == "true"

    if not partial_refresh:
        # templates.TemplateResponse("tasks.jhtml", ctx)
        return await response_generator(
            request,
            "tasks.jhtml",
            {
                "curr_user": user,
                "tasks": tasks,
                "uid2name": uid2name,
            },
        )

    tasks = [t for t in tasks if t.category in (category or [])]

    show_solved = "show_solved" in request.query_params
    if not show_solved and user:
        tasks = [t for t in tasks if not t.solved_by(user)]

    return await response_generator(
        request,
        "partials/task_container.jhtml",
        {
            "curr_user": user,
            "tasks": tasks,
            "uid2name": uid2name,
        },
    )


@router.get("/tasks/{task_id}")
async def tasks_get_task(
    request: Request,
    resp: Response,
    task_id: uuid.UUID,
    user: auth.CURR_USER_SAFE,
):
    task = await api_tasks.api_task_get(task_id, user)
    return await response_generator(
        request,
        "task.jhtml",
        {
            "curr_user": user,
            "task": task,
        },
    )


@router.get("/scoreboard")
async def scoreboard_page(request: Request, user: auth.CURR_USER_SAFE):
    tasks = await api_tasks.api_tasks_get(user)
    scoreboard = await api_users.api_scoreboard_get_internal_shrinked()

    partial_refresh = request.headers.get("hx-request") == "true"

    return await response_generator(
        request,
        "scoreboard.jhtml" if not partial_refresh else "partials/scoreboard_table.jhtml",
        {
            "curr_user": user,
            "scoreboard": scoreboard,
            "enumerate": enumerate,
            "all_tasks": tasks,
        },
    )


@router.get("/profile")
async def profile_page(request: Request, user: auth.CURR_USER_SAFE):
    return await response_generator(
        request,
        "profile.jhtml",
        {
            "curr_user": user,
        },
    )


@router.get("/login")
async def login_get(req: Request, resp: Response, user: auth.CURR_USER_SAFE):
    return await response_generator(
        req,
        "login.jhtml",
        {
            "curr_user": user,
            "auth_ways": schema.auth.ENABLED_AUTH_WAYS,
        },
    )
