import logging
import uuid

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from fastapi.routing import APIRouter

from ... import auth, config, schema
from ...api import api_tasks as api_tasks
from ...api import api_users as api_users
from ...api.admin import admin_checker
from ...api.admin import admin_tasks as api_admin_tasks
from ...api.admin import admin_users as api_admin_users
from ...ws import ws_manager

logger = logging.getLogger("yatb.view")

from .. import response_generator  # noqa

router = APIRouter(
    prefix="/admin",
    tags=["admin_view"],
)


@router.get("/")
async def admin_index(req: Request, resp: Response, user: schema.User = Depends(admin_checker)):
    return response_generator(
        req,
        "admin/index.jhtml",
        {
            "request": req,
            "curr_user": user,
        },
        ignore_admin=False,
    )


@router.get("/tasks")
async def admin_tasks(req: Request, resp: Response, user: schema.User = Depends(admin_checker)):
    tasks_list = await api_tasks.api_tasks_get(user)
    return response_generator(
        req,
        "admin/tasks_admin.jhtml",
        {
            "request": req,
            "curr_user": user,
            "task_class": schema.Task,
            "task_form_class": schema.TaskForm,
            "tasks_list": tasks_list,
        },
        ignore_admin=False,
    )


@router.get("/task/{task_id}")
async def admin_task_get(req: Request, resp: Response, task_id: uuid.UUID, user: schema.User = Depends(admin_checker)):
    tasks_list = await api_tasks.api_tasks_get(user)
    selected_task = await api_tasks.api_task_get(task_id, user)
    return response_generator(
        req,
        "admin/tasks_admin.jhtml",
        {
            "request": req,
            "curr_user": user,
            "task_class": schema.Task,
            "task_form_class": schema.TaskForm,
            "tasks_list": tasks_list,
            "selected_task": selected_task,
        },
        ignore_admin=False,
    )


@router.get("/users")
async def admin_users(req: Request, resp: Response, user: schema.User = Depends(admin_checker)):
    users_dict = await api_admin_users.api_admin_users_internal()
    return response_generator(
        req,
        "admin/users_admin.jhtml",
        {
            "request": req,
            "curr_user": user,
            "user_class": schema.User,
            # "user_form_class": schema.UserForm,
            "users_list": users_dict.values(),
        },
        ignore_admin=False,
    )


@router.get("/user/{user_id}")
async def admin_user_get(req: Request, resp: Response, user_id: uuid.UUID, user: schema.User = Depends(admin_checker)):
    users_dict = await api_admin_users.api_admin_users_internal()
    selected_user = await api_admin_users.api_admin_user_get_internal(user_id)
    return response_generator(
        req,
        "admin/users_admin.jhtml",
        {
            "request": req,
            "curr_user": user,
            "user_class": schema.User,
            # "user_form_class": schema.UserForm,
            "users_list": users_dict.values(),
            "selected_user": selected_user,
        },
        ignore_admin=False,
    )


async def get_token(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    if token and token == config.settings.WS_API_TOKEN:
        return token

    raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)


@router.websocket("/ws")
async def websocker_ep(
    websocket: WebSocket,
    token: str = Depends(get_token),
):
    logger.info(f"{token= } connected to WS")
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({"ping": "ping"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
