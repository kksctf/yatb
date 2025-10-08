import asyncio
import datetime
import gettext
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypeAlias

from fastapi import BackgroundTasks, Depends, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute as _APIRoute
from fastapi.routing import APIRouter
from fastapi.templating import Jinja2Templates
from starlette.routing import Router
from starlette.templating import _TemplateResponse

from yatb import auth, i18n, schema
from yatb.api import tasks
from yatb.config import settings
from yatb.db.task import TaskDB
from yatb.db.user import UserDB
from yatb.utils import md
from yatb.utils.httpx import IS_HTTPX
from yatb.utils.log_helper import get_logger

logger = get_logger("view")

_base_path = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=_base_path / "templates")

TRANSLATIONS = {
    lang: gettext.translation(
        domain="messages",
        localedir=Path(__file__).parent.parent / "locale",
        languages=[lang],
        fallback=True,
    )
    for lang in i18n.SUPPORTED
}

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


def _(text: str, request: Request) -> str:
    return TRANSLATIONS[request.state.lang].gettext(text)


templates.env.globals["version_string"] = version_string
templates.env.globals["len"] = len
templates.env.globals["template_format_time"] = schema.task.template_format_time
templates.env.globals["set"] = set
templates.env.globals["str"] = str
templates.env.globals["isinstance"] = isinstance
templates.env.globals["enumerate"] = enumerate

templates.env.globals["DEBUG"] = settings.DEBUG
templates.env.globals["FLAG_BASE"] = settings.FLAG_BASE
templates.env.globals["CTF_NAME"] = settings.CTF_NAME
templates.env.globals["EVENT_START_TIME"] = settings.EVENT_START_TIME
templates.env.globals["EVENT_END_TIME"] = settings.EVENT_END_TIME
templates.env.globals["NOW"] = lambda: datetime.datetime.now(datetime.UTC)

templates.env.globals["_"] = _

from . import admin  # noqa

router.include_router(admin.router)


@dataclass
class _Cache:
    user_id_to_username: dict[schema.UserID, str]


async def get_cache(request: Request) -> _Cache:
    users = await UserDB.get_all_projected(UserDB.ScoreboardProjection)
    uid2name = {uuid: user.username for uuid, user in users.items()}

    return _Cache(user_id_to_username=uid2name)


Cache: TypeAlias = Annotated[_Cache, Depends(get_cache)]


@router.get("/")
@router.get("/index")
async def index(request: Request, user: auth.CURR_USER_SAFE) -> HTMLResponse:
    return await response_generator(request, "index.jhtml", {"curr_user": user})


@router.get("/tasks")
async def tasks_page(
    req: Request,
    is_httpx: IS_HTTPX,
    cache: Cache,
    user: auth.CURR_USER_SAFE,
    tasks: tasks.VISIBLE_TASKS,
    show_solved: bool | None = Query(default=None),
    category: list[str] | None = Query(None),
) -> HTMLResponse:
    categories = {t.category for t in tasks}

    if not is_httpx:
        return await response_generator(
            req,
            "tasks.jhtml",
            {
                "curr_user": user,
                "tasks": tasks,
                "categories": categories,
                "uid2name": cache.user_id_to_username,
            },
        )

    tasks = [t for t in tasks if t.category in (category or [])]

    if not show_solved and user:
        tasks = [t for t in tasks if not t.is_solved_by(user)]

    return await response_generator(
        req,
        "partials/task_container.jhtml",
        {
            "curr_user": user,
            "tasks": tasks,
            "uid2name": cache.user_id_to_username,
        },
    )


@router.get("/tasks/{task_id}")
async def one_task_page(
    req: Request,
    cache: Cache,
    task: tasks.CURRENT_TASK,
    user: auth.CURR_USER_SAFE,
) -> HTMLResponse:
    return await response_generator(
        req,
        "task.jhtml",
        {
            "curr_user": user,
            "selected_task": task,
            "uid2name": cache.user_id_to_username,
        },
    )


@router.get("/scoreboard")
async def scoreboard_page(
    request: Request,
    is_httpx: IS_HTTPX,
    user: auth.CURR_USER_SCOREBOARD,
    tasks: tasks.VISIBLE_TASKS,
) -> HTMLResponse:
    scoreboard = await UserDB.get_filtered_projected_scoreboard()

    return await response_generator(
        request,
        "scoreboard.jhtml" if not is_httpx else "partials/scoreboard_table.jhtml",
        {
            "curr_user": user,
            "scoreboard": scoreboard,
            "all_tasks": tasks,
        },
    )


@router.get("/profile")
async def profile_page(request: Request, user: auth.CURR_USER_SAFE) -> HTMLResponse:
    return await response_generator(
        request,
        "profile.jhtml",
        {
            "curr_user": user,
        },
    )


@router.get("/login")
async def login_page(req: Request, user: auth.CURR_USER_SAFE) -> HTMLResponse:
    return await response_generator(
        req,
        "login.jhtml",
        {
            "curr_user": user,
            "auth_ways": schema.auth.ENABLED_AUTH_WAYS,
        },
    )
