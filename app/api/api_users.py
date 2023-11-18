import uuid
from collections.abc import Sequence
from typing import Iterable, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .. import auth, schema
from ..config import settings
from ..db.beanie import TaskDB, UserDB
from .api_tasks import api_tasks_get

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

_T = TypeVar("_T", schema.User, UserDB.ScoreboardProjection)


def filter_scoreboard(users: Iterable[_T]) -> Sequence[_T]:
    ret = users

    if not settings.DEBUG:
        ret = filter(lambda x: not x.is_admin, ret)

    ret = sorted(
        ret,
        key=lambda i: (
            i.get_last_solve_time()[1],
            i.score * -1,
        ),
        reverse=False,
    )

    return ret


async def api_scoreboard_get_internal() -> Sequence[schema.User]:
    users = await UserDB.get_all()

    return filter_scoreboard(users.values())


async def api_scoreboard_get_internal_shrinked() -> Sequence[UserDB.ScoreboardProjection]:
    users = await UserDB.get_all_projected(UserDB.ScoreboardProjection)

    return filter_scoreboard(users.values())


@router.get("/scoreboard")
async def api_scoreboard_get() -> Sequence[schema.User.public_model]:
    users = await api_scoreboard_get_internal()
    return users  # noqa: RET504


@router.get("/ctftime_scoreboard")
async def api_task_get_ctftime_scoreboard(*, fullScoreboard: bool = False):
    scoreboard = await api_scoreboard_get_internal()
    standings = []
    tasks = None
    full_tasks_list = None
    if fullScoreboard:
        tasks_list = await api_tasks_get(None)  # we don't need to export hidden tasks
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
