from dataclasses import dataclass
from typing import Annotated, TypeAlias

from fastapi import Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from yatb import auth, schema
from yatb.api import tasks
from yatb.db.user import UserDB
from yatb.ui import get_ui_state
from yatb.utils import countries
from yatb.utils.httpx import IS_HTTPX
from yatb.utils.log_helper import get_logger

from .util import response_generator

logger = get_logger("view")

router = APIRouter(
    prefix="",
    tags=["view"],
)

from . import actions, admin, scoreboard  # noqa

router.include_router(admin.router)
router.include_router(scoreboard.router)
router.include_router(actions.router)


@dataclass
class _Cache:
    user_id_to_username: dict[schema.UserID, str]


async def get_cache(request: Request) -> _Cache:
    users = await UserDB.get_all_projected(UserDB.ScoreboardProjection)
    uid2name = {uuid: user.display_name for uuid, user in users.items()}

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


@router.get("/profile")
async def profile_page(request: Request, user: auth.CURR_USER_OR_REDIRECT_LOGIN) -> HTMLResponse:
    lang = get_ui_state(request).lang
    return await response_generator(
        request,
        "profile.jhtml",
        {
            "curr_user": user,
            # Country names are localized, and the render happens in an executor thread
            # where i18n.current_lang is only set for the template's own gettext calls —
            # so resolve them here rather than through a Jinja global.
            "countries": countries.country_list(lang),
            "country_name": lambda code: countries.country_name(code, lang),
        },
    )


@router.get("/login")
async def login_page(req: Request, user: auth.CURR_USER_SAFE) -> HTMLResponse:
    return await response_generator(
        req,
        "login.jhtml",
        {
            "curr_user": user,
            "auth_ways": [i for i in schema.auth.ENABLED_AUTH_WAYS if not i.FAKE],
        },
    )
