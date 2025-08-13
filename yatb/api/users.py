import uuid
from collections.abc import Iterable, Sequence
from typing import TypeVar

from fastapi import APIRouter, HTTPException, Request, Response, status

from yatb import auth, schema
from yatb.config import settings
from yatb.db import TaskDB, UserDB

from .tasks import get_tasks

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/scoreboard")
async def api_scoreboard_get() -> Sequence[schema.User.public_model]:
    return await UserDB.get_filtered_scoreboard()


@router.get("/ctftime_scoreboard")
async def api_task_get_ctftime_scoreboard(*, fullScoreboard: bool = False):  # noqa: N803
    scoreboard = await UserDB.get_filtered_scoreboard()
    standings = []
    tasks = None
    full_tasks_list = None

    if fullScoreboard:
        tasks_list = await get_tasks(None)  # we don't need to export hidden tasks
        full_tasks_list = await TaskDB.get_all()
        tasks = [x.task_name for x in tasks_list]

    for i, user in enumerate(scoreboard):
        obj = {
            "pos": i + 1,
            "team": user.username,
            "score": user.score,
        }

        if fullScoreboard and full_tasks_list:
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


@router.get("/me")
async def api_users_me(user: auth.CURR_USER) -> schema.User.public_model:
    return user


@router.get("/logout")
async def api_users_logout(req: Request, resp: Response, user: auth.CURR_USER) -> str:
    resp.delete_cookie(key="access_token")
    resp.status_code = status.HTTP_307_TEMPORARY_REDIRECT
    resp.headers["Location"] = str(req.url_for("index"))
    return "ok"


@router.get("/{user_id}")
async def api_users_get(user_id: uuid.UUID, user: auth.CURR_USER) -> schema.User.public_model:
    req_user = await UserDB.find_by_user_uuid(user_id)
    if not req_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ID not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return req_user


@router.get("/{user_id}/username")
async def api_users_get_username(user_id: uuid.UUID) -> str:
    req_user = await UserDB.find_by_user_uuid(user_id)
    if not req_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ID not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return req_user.username
