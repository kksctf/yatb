from app.api.api_tasks import api_tasks_get_internal
import uuid
import aiohttp
from typing import List, Optional
from datetime import timedelta

from fastapi import Request, Response, HTTPException, status, Depends, APIRouter
from starlette.responses import RedirectResponse

from . import logger
from .. import schema, auth, config, db
from ..utils import metrics

router = APIRouter(
    prefix="/users",
    tags=["users"]
)


async def api_scoreboard_get_internal() -> List[schema.User]:
    users = await db.get_all_users()
    if not config._DEGUG:
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
    response_model_exclude=schema.User.get_exclude_fields()
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
        tasks_list = await api_tasks_get_internal(False)  # we don't need to export hidden tasks
        full_tasks_list = await db.get_all_tasks()  # this used only for uuid resolve # TODO: maybe it can be done normally?
        tasks = list(map(lambda x: x.task_name, tasks_list))
    for i, user in enumerate(scoreboard):
        obj = {
            "pos": i+1,
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

# =============== ONLY DEBUG ===============


@router.post("/login")
async def api_token(resp: Response, form_data: schema.UserForm):
    if not config._DEGUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No.",
        )
    user = await auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = auth.create_user_token(user)
    resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

    return "ok"


@router.post("/register")
async def api_users_register(resp: Response, form_data: schema.UserForm):
    if not config._DEGUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No.",
        )
    if await db.check_user(form_data.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Username exists",
        )
    user = await db.insert_user(form_data.username, form_data.password)

    access_token = auth.create_user_token(user)
    resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

    return "ok"
# =============== ONLY DEBUG ===============


@router.get("/oauth_callback")
async def api_oauth_callback(req: Request, resp: Response, code: str, state: str):
    async with aiohttp.ClientSession() as session:
        oauth_token = await (
            await session.post(
                config.OAUTH_TOKEN_ENDPOINT,
                params={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": req.url_for("api_oauth_callback"),
                    "client_id": config.OAUTH_CLIENT_ID,
                    "client_secret": config.OAUTH_CLIENT_SECRET,
                }
            )
        ).json()
        logger.debug(f"oauth token data: {oauth_token}")
        if "access_token" not in oauth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CTFTime error",
            )

        user_data = await (await session.get(config.OAUTH_API_ENDPOINT, headers={"Authorization": f"Bearer {oauth_token['access_token']}"})).json()
        logger.debug(f"User api token data: {user_data}")
        if "team" not in user_data or "id" not in user_data["team"] or "name" not in user_data["team"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CTFTime error",
            )

        user = await db.get_user_oauth_id(user_data["team"]["id"])
        if user is None:
            user = await db.insert_oauth_user(user_data["team"]["id"], user_data["team"]["name"], user_data["team"].get("country", ""))
            metrics.users.inc()

        metrics.logons_per_user.labels(user_id=user.user_id, username=user.username).inc()

        access_token = auth.create_user_token(user)
        resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

        resp.status_code = status.HTTP_307_TEMPORARY_REDIRECT
        resp.headers["Location"] = req.url_for("index")
    return "ok"


@router.get(
    "/me",
    response_model=schema.User,
    response_model_include=schema.User.get_include_fieds(False),
    response_model_exclude=schema.User.get_exclude_fields()
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
    response_model_exclude=schema.User.get_exclude_fields()
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
