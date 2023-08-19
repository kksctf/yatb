import uuid
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .. import auth, schema
from ..config import settings
from ..db.beanie import UserDB
from .api_tasks import api_tasks_get

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


async def api_scoreboard_get_internal() -> Sequence[schema.User]:
    users = await UserDB.get_all()
    if not settings.DEBUG:  # noqa: SIM108
        users = filter(lambda x: not x.is_admin, users.values())
    else:
        users = users.values()
    users = sorted(users, key=lambda i: i.get_last_solve_time()[1])
    users = sorted(users, key=lambda i: i.score, reverse=True)
    return users  # noqa: RET504


@router.get("/scoreboard")
async def api_scoreboard_get() -> Sequence[schema.User.public_model]:
    users = await api_scoreboard_get_internal()
    return users  # noqa: RET504


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
