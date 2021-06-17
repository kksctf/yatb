import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import parse_obj_as
from starlette.routing import Router

from .. import auth, db, schema
from ..api import api_tasks as api_tasks
from ..api import api_users as api_users
from ..config import settings

logger = logging.getLogger("yatb.view")

_base_path = os.path.dirname(os.path.abspath(__file__))
templ = Jinja2Templates(directory=os.path.join(_base_path, "templates"))

router = APIRouter(
    prefix="",
    tags=["view"],
)


def route_generator(req: Request, base_path="/api") -> Dict[str, str]:
    router: Router = req.scope["router"]
    ret = {}
    for r in router.routes:
        if r.path.startswith(base_path):
            dummy_params = {i: f"NONE_{i}" for i in set(r.param_convertors.keys())}
            ret[r.name] = req.url_for(name=r.name, **dummy_params)
    return ret


def response_generator(
    req: Request,
    filename: str,
    context: dict = {},
    status_code: int = 200,
    headers: dict = None,
    media_type: str = None,
    background=None,
) -> Response:
    context_base = {
        "request": req,
        "api_list": route_generator(req),
    }
    context_base.update(context)
    return templ.TemplateResponse(
        name=filename,
        context=context_base,
        status_code=status_code,
        headers=headers,
        media_type=media_type,
        background=background,
    )


def version_string():
    return f"kks-tb-{settings.VERSION}"


templ.env.globals["version_string"] = version_string
templ.env.globals["len"] = len
templ.env.globals["template_format_time"] = schema.task.template_format_time
templ.env.globals["set"] = set
templ.env.globals["isinstance"] = isinstance

templ.env.globals["DEBUG"] = settings.DEBUG
templ.env.globals["FLAG_BASE"] = settings.FLAG_BASE
templ.env.globals["CTF_NAME"] = settings.CTF_NAME
templ.env.globals["OAUTH_CONFIG"] = {
    "OAUTH_CLIENT_ID": settings.OAUTH_CLIENT_ID,
    "OAUTH_CLIENT_SECRET": settings.OAUTH_CLIENT_SECRET,
    "OAUTH_ENDPOINT": settings.OAUTH_ENDPOINT,
    # ""
}


async def get_user_safe(request: Request) -> Optional[schema.User]:
    user = None
    try:
        user = await auth.get_current_user(await auth.oauth2_scheme(request))
    except HTTPException:
        user = None
    return user


from . import admin  # noqa

router.include_router(admin.router)


@router.get("/")
@router.get("/index")
async def index(req: Request, resp: Response):
    return await tasks_get_all(req, resp)


@router.get("/tasks")
async def tasks_get_all(req: Request, resp: Response):
    user = await get_user_safe(req)
    admin = False
    if user and user.is_admin:
        admin = True
    tasks_list = await api_tasks.api_tasks_get_internal(admin)
    return response_generator(
        req,
        "tasks.jhtml",
        {
            "request": req,
            "curr_user": user,
            "tasks": tasks_list,
        },
    )


@router.get("/scoreboard")
async def scoreboard_get(req: Request, resp: Response):
    scoreboard = await api_users.api_scoreboard_get_internal()
    return response_generator(
        req,
        "scoreboard.jhtml",
        {
            "request": req,
            "curr_user": await get_user_safe(req),
            "scoreboard": scoreboard,
            "enumerate": enumerate,
        },
    )


@router.get("/login")
async def login_get(req: Request, resp: Response):
    return response_generator(
        req,
        "login.jhtml",
        {
            "request": req,
            "curr_user": await get_user_safe(req),
        },
    )


@router.get("/tasks/{task_id}")
async def tasks_get_task(req: Request, resp: Response, task_id: uuid.UUID):
    task = await api_tasks.api_task_get_internal(task_id)
    return response_generator(
        req,
        "task.jhtml",
        {
            "request": req,
            "curr_user": await get_user_safe(req),
            "selected_task": task,
        },
    )
