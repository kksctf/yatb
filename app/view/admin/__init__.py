import uuid
import logging

from fastapi import FastAPI, Cookie, Request, Response, HTTPException, status, Depends
from fastapi.routing import APIRouter

from ... import auth, config, schema

from ...api import api_tasks as api_tasks
from ...api import api_users as api_users

from ...api.admin import admin_tasks as api_admin_tasks
from ...api.admin import admin_users as api_admin_users
from ...api.admin import admin_checker

logger = logging.getLogger("yatb.view")

from .. import templ  # noqa

router = APIRouter(
    prefix="/admin",
    tags=["admin_view"],
)


@router.get("/")
async def admin_index(request: Request, user: schema.User = Depends(admin_checker)):
    return templ.TemplateResponse("admin/index.jhtml", {
        "request": request,
        "curr_user": user,
    })


@router.get("/tasks")
async def admin_tasks(request: Request, user: schema.User = Depends(admin_checker)):
    tasks_list = await api_tasks.api_tasks_get_internal(admin=True)
    return templ.TemplateResponse("admin/tasks_admin.jhtml", {
        "request": request,
        "curr_user": user,
        "task_class": schema.Task,
        "task_form_class": schema.TaskForm,
        "tasks_list": tasks_list,
    })


@router.get("/task/{task_id}")
async def admin_task_get(request: Request, task_id: uuid.UUID, user: schema.User = Depends(admin_checker)):
    tasks_list = await api_tasks.api_tasks_get_internal(admin=True)
    selected_task = await api_tasks.api_task_get_internal(task_id, admin=True)
    return templ.TemplateResponse("admin/tasks_admin.jhtml", {
        "request": request,
        "curr_user": user,
        "task_class": schema.Task,
        "task_form_class": schema.TaskForm,
        "tasks_list": tasks_list,
        "selected_task": selected_task
    })


@router.get("/users")
async def admin_users(request: Request, user: schema.User = Depends(admin_checker)):
    users_dict = await api_admin_users.api_admin_users_internal()
    return templ.TemplateResponse("admin/users_admin.jhtml", {
        "request": request,
        "curr_user": user,
        "user_class": schema.User,
        "user_form_class": schema.UserForm,
        "users_list": users_dict.values()
    })


@router.get("/user/{user_id}")
async def admin_user_get(request: Request, user_id: uuid.UUID, user: schema.User = Depends(admin_checker)):
    users_dict = await api_admin_users.api_admin_users_internal()
    selected_user = await api_admin_users.api_admin_user_get_internal(user_id)
    return templ.TemplateResponse("admin/users_admin.jhtml", {
        "request": request,
        "curr_user": user,
        "user_class": schema.User,
        "user_form_class": schema.UserForm,
        "users_list": users_dict.values(),
        "selected_user": selected_user,
    })
