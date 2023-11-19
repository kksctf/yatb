import asyncio
import uuid
from collections.abc import Mapping
from pathlib import Path

from fastapi import BackgroundTasks, Depends, Request, Response
from fastapi.routing import APIRoute as _APIRoute
from fastapi.routing import APIRouter
from fastapi.templating import Jinja2Templates
from formgen.gen2 import Context as FormContext
from formgen.gen2 import Contexts as FormContexts
from formgen.gen2 import FieldType as FormFieldType
from formgen.gen2 import generate_form
from starlette.routing import Router
from starlette.templating import _TemplateResponse

from .. import auth, schema
from ..api import api_tasks, api_users
from ..config import settings
from ..utils.log_helper import get_logger

logger = get_logger("view")

_base_path = Path(__file__).resolve().parent
templ = Jinja2Templates(directory=_base_path / "templates")

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
        lambda: templ.TemplateResponse(
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


templ.env.globals["version_string"] = version_string
templ.env.globals["len"] = len
templ.env.globals["template_format_time"] = schema.task.template_format_time
templ.env.globals["set"] = set
templ.env.globals["isinstance"] = isinstance

templ.env.globals["DEBUG"] = settings.DEBUG
templ.env.globals["FLAG_BASE"] = settings.FLAG_BASE
templ.env.globals["CTF_NAME"] = settings.CTF_NAME

templ.env.globals["generate_form"] = generate_form
templ.env.globals["FormFieldType"] = FormFieldType
templ.env.globals["FormContext"] = FormContext
templ.env.globals["FormContexts"] = FormContexts

from . import admin  # noqa

router.include_router(admin.router)


@router.get("/")
@router.get("/index")
async def index(req: Request, resp: Response, user: auth.CURR_USER_SAFE):
    return await tasks_get_all(req, resp, user)


@router.get("/tasks")
async def tasks_get_all(req: Request, resp: Response, user: auth.CURR_USER_SAFE):
    tasks_list = await api_tasks.api_tasks_get(user)
    return await response_generator(
        req,
        "tasks.jhtml",
        {
            "request": req,
            "curr_user": user,
            "tasks": tasks_list,
        },
    )


@router.get("/scoreboard")
async def scoreboard_get(req: Request, resp: Response, user: auth.CURR_USER_SAFE):
    tasks_list = await api_tasks.api_tasks_get(user)
    scoreboard = await api_users.api_scoreboard_get_internal_shrinked()

    return await response_generator(
        req,
        "scoreboard.jhtml",
        {
            "request": req,
            "curr_user": user,
            "scoreboard": scoreboard,
            "enumerate": enumerate,
            "all_tasks": tasks_list,
        },
    )


@router.get("/login")
async def login_get(req: Request, resp: Response, user: auth.CURR_USER_SAFE):
    return await response_generator(
        req,
        "login.jhtml",
        {
            "request": req,
            "curr_user": user,
            "auth_ways": schema.auth.ENABLED_AUTH_WAYS,
        },
    )


@router.get("/tasks/{task_id}")
async def tasks_get_task(
    req: Request,
    resp: Response,
    task_id: uuid.UUID,
    user: auth.CURR_USER_SAFE,
):
    task = await api_tasks.api_task_get(task_id, user)
    return await response_generator(
        req,
        "task.jhtml",
        {
            "request": req,
            "curr_user": user,
            "selected_task": task,
        },
    )
