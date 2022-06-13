import uuid
from datetime import timedelta
from typing import List, Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.responses import RedirectResponse

from .. import auth, db, schema
from ..config import settings
from ..utils import metrics
from . import logger
from .api_tasks import api_tasks_get

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


async def api_scoreboard_get_internal() -> List[schema.User]:
    users = await db.get_all_users()
    if not settings.DEBUG:
        users = filter(lambda x: not x.is_admin, users.values())
    else:
        users = users.values()
    users = sorted(users, key=lambda i: i.get_last_solve_time()[1])
    users = sorted(users, key=lambda i: i.score, reverse=True)
    return users


@router.get(
    "/scoreboard",
    response_model=List[schema.User],
    response_model_include=schema.User.get_include_fieds(False),
    response_model_exclude=schema.User.get_exclude_fields(),
)
async def api_scoreboard_get():
    users = await api_scoreboard_get_internal()
    return users


@router.get("/ctftime_scoreboard")
async def api_task_get_ctftime_scoreboard(fullScoreboard: bool = False):
    scoreboard = await api_scoreboard_get_internal()
    standings = []
    tasks = None
    full_tasks_list = None
    if fullScoreboard:
        tasks_list = await api_tasks_get(None)  # we don't need to export hidden tasks
        full_tasks_list = (
            await db.get_all_tasks()
        )  # this used only for uuid resolve # TODO: maybe it can be done normally?
        tasks = list(map(lambda x: x.task_name, tasks_list))
    for i, user in enumerate(scoreboard):
        obj = {
            "pos": i + 1,
            "team": user.username,
            "score": user.score,
        }
        if fullScoreboard:
            obj["taskStats"] = {}
            for solved_task in user.solved_tasks:
                obj["taskStats"][full_tasks_list[solved_task].task_name] = {
                    "points": full_tasks_list[solved_task].scoring.points,
                    "time": user.solved_tasks[solved_task],
                }
        standings.append(obj)
    if fullScoreboard:
        return {
            "tasks": tasks,
            "standings": standings,
        }
    else:
        return {
            "standings": standings,
        }


@router.get(
    "/me",
    response_model=schema.User,
    response_model_include=schema.User.get_include_fieds(False),
    response_model_exclude=schema.User.get_exclude_fields(),
)
async def api_users_me(user: schema.User = Depends(auth.get_current_user)):
    return user


@router.get("/logout")
async def api_users_logout(req: Request, resp: Response, user: schema.User = Depends(auth.get_current_user)):
    resp.delete_cookie(key="access_token")
    resp.status_code = status.HTTP_307_TEMPORARY_REDIRECT
    resp.headers["Location"] = req.url_for("index")
    return "ok"


@router.get(
    "/{user_id}",
    response_model=schema.User,
    response_model_include=schema.User.get_include_fieds(False),
    response_model_exclude=schema.User.get_exclude_fields(),
)
async def api_users_get(user_id: uuid.UUID, user: schema.User = Depends(auth.get_current_user)):
    req_user = await db.get_user_uuid(user_id)
    if not req_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ID not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return req_user


@router.get("/{user_id}/username", response_model=str)
async def api_users_get_username(user_id: uuid.UUID):
    req_user = await db.get_user_uuid(user_id)
    if not req_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ID not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return req_user.username
