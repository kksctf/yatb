import os
import uuid
import logging
from typing import List, Optional, Any
from datetime import timedelta
from datetime import datetime
from fastapi.routing import APIRouter
from pydantic import parse_obj_as

from fastapi import FastAPI, Cookie, Request, Response, HTTPException, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import schema, auth, db
from ..config import settings

from ..api import api_tasks as api_tasks
from ..api import api_users as api_users

logger = logging.getLogger("yatb.view")

_base_path = os.path.dirname(os.path.abspath(__file__))
templ = Jinja2Templates(directory=os.path.join(_base_path, "templates"))
router = APIRouter(
    prefix="",
    tags=["view"]
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
async def index(request: Request):
    return await tasks_get_all(request)


@router.get("/tasks")
async def tasks_get_all(request: Request):
    user = await get_user_safe(request)
    admin = False
    if user and user.is_admin:
        admin = True
    tasks_list = await api_tasks.api_tasks_get_internal(admin)
    return templ.TemplateResponse(
        "tasks.jhtml",
        {
            "request": request,
            "curr_user": user,
            "tasks": tasks_list,
        },
    )


@router.get("/scoreboard")
async def scoreboard_get(request: Request):
    scoreboard = await api_users.api_scoreboard_get_internal()
    return templ.TemplateResponse(
        "scoreboard.jhtml",
        {
            "request": request,
            "curr_user": await get_user_safe(request),
            "scoreboard": scoreboard,
            "enumerate": enumerate,
        },
    )


@router.get("/login")
async def login_get(request: Request):
    return templ.TemplateResponse(
        "login.jhtml",
        {
            "request": request,
            "curr_user": await get_user_safe(request),
        },
    )


@router.get("/tasks/{task_id}")
async def tasks_get_task(request: Request, task_id: uuid.UUID):
    task = await api_tasks.api_task_get_internal(task_id)
    return templ.TemplateResponse(
        "task.jhtml",
        {
            "request": request,
            "curr_user": await get_user_safe(request),
            "selected_task": task,
        },
    )
