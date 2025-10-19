from collections.abc import Mapping
from typing import Annotated, Any

from fastapi import (
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from fastui import AnyComponent, FastUI, prebuilt_html
from fastui import components as c
from fastui.components.display import DisplayLookup
from fastui.events import BackEvent, GoToEvent
from fastui.forms import SelectSearchResponse, fastui_form
from pydantic import BaseModel, Field, field_validator

from yatb import schema
from yatb.api.admin import admin_tasks as api_admin_tasks
from yatb.api.admin import admin_users as api_admin_users
from yatb.auth import CURR_ADMIN
from yatb.utils.log_helper import get_logger

c.Link.model_rebuild()
c.ModelForm.model_rebuild()

logger = get_logger("view")

base_router = APIRouter(
    prefix="/ng",
    tags=["admin-ng"],
)

api_rotuer = APIRouter(
    prefix="/api/admin/ng",
    tags=["admin-ng-api"],
)


def url_gen(req: Request, path: str) -> str:
    return str(req.url_for("admin_ng_html_landing", path=path))


def base_page(req: Request, *components: AnyComponent, title: str | None = None) -> list[AnyComponent]:
    return [
        c.PageTitle(text=f"YATB Admin — {title if title else 'Root'}"),
        c.Navbar(
            title="YATB Admin",
            title_event=GoToEvent(url=url_gen(req, "")),
            start_links=[
                c.Link(
                    components=[c.Text(text="Back to board")],
                    on_click=GoToEvent(url=str(req.url_for("index"))),
                ),
                c.Link(
                    components=[c.Text(text="Tasks")],
                    on_click=GoToEvent(url=url_gen(req, "tasks")),
                    active="startswith:/tasks",
                ),
                c.Link(
                    components=[c.Text(text="Users")],
                    on_click=GoToEvent(url=url_gen(req, "users")),
                    active="startswith:/users",
                ),
                # c.Link(
                #     components=[c.Text(text="Components")],
                #     on_click=GoToEvent(url="/components"),
                #     active="startswith:/components",
                # ),
            ],
        ),
        c.Page(
            components=[
                *((c.Heading(text=title),) if title else ()),
                *components,
            ],
        ),
    ]


@api_rotuer.get("", response_model=FastUI, response_model_exclude_none=True)
async def admin_ng_index(req: Request, admin: CURR_ADMIN) -> list[AnyComponent]:
    return base_page(req, c.Text(text="..."))


@api_rotuer.get("/tasks", response_model=FastUI, response_model_exclude_none=True)
async def admin_ng_tasks(req: Request, admin: CURR_ADMIN) -> list[AnyComponent]:
    tasks = await api_admin_tasks.api_admin_tasks(admin)

    return base_page(
        req,
        # c.ModelForm(submit_url="", model=schema.TaskForm),
        c.Table(
            data=[
                schema.Task.admin_model.model_validate(v.model_dump())
                for i, v in sorted(tasks.items(), key=lambda iv: iv[1].task_name)
            ],
            data_model=schema.Task.admin_model,
            columns=[
                DisplayLookup(field="task_name", title="Name", on_click=GoToEvent(url=url_gen(req, "task/{task_id}"))),
                DisplayLookup(field="category", title="Category"),
                DisplayLookup(field="points", title="Points"),
                DisplayLookup(field="solves", title="Solve Count"),
                DisplayLookup(field="hidden", title="Hidden?"),
            ],
        ),
        title="Tasks",
    )


@api_rotuer.get("/task/{task_id}", response_model=FastUI, response_model_exclude_none=True)
async def admin_ng_task(req: Request, admin: CURR_ADMIN, raw_task: api_admin_tasks.CURR_TASK) -> list[AnyComponent]:
    sanitized_task = schema.Task.admin_model.model_validate(raw_task.model_dump())

    return base_page(
        req,
        c.Heading(text=sanitized_task.task_name, level=2),
        c.Link(components=[c.Text(text="Back")], on_click=BackEvent()),
        c.Details(
            data=sanitized_task,
            # fields=[
            #     DisplayLookup(field="task_id", title="ID"),
            # ],
        ),
        title=f"Task - {sanitized_task.task_name}",
    )


@api_rotuer.get("/users", response_model=FastUI, response_model_exclude_none=True)
async def admin_ng_users(req: Request, admin: CURR_ADMIN) -> list[AnyComponent]:
    users: Mapping[schema.UserID, schema.User] = await api_admin_users.api_admin_users(admin)
    sorted_users = sorted(users.items(), key=lambda iv: iv[1].username)
    sorted_users = sorted(sorted_users, key=lambda iv: iv[1].is_admin)

    return base_page(
        req,
        c.Table(
            data=[schema.User.admin_model.model_validate(v.model_dump()) for i, v in sorted_users],
            data_model=schema.User.admin_model,
            columns=[
                DisplayLookup(field="username", title="Name", on_click=GoToEvent(url=url_gen(req, "user/{user_id}"))),
                DisplayLookup(field="is_admin", title="Admin"),
                # DisplayLookup(field="points", title="Points"),
                # DisplayLookup(field="solves", title="Solve Count"),
            ],
        ),
        title="Users",
    )


@api_rotuer.get("/user/search")
async def users_search(
    request: Request,
    admin: CURR_ADMIN,
    q: str,
    *,
    show_admin: bool = False,
) -> SelectSearchResponse:
    users: Mapping[schema.UserID, schema.User] = await api_admin_users.api_admin_users(admin)

    ret = []

    q = q.lower()

    for user in users.values():
        if q not in user.username.lower():
            continue

        if not show_admin and user.is_admin:
            continue

        ret.append(
            {
                "value": f"{user.user_id}",
                "label": user.username,
            },
        )

    return SelectSearchResponse(options=ret)


@api_rotuer.get("/user/{user_id}", response_model=FastUI, response_model_exclude_none=True)
async def admin_ng_user(req: Request, admin: CURR_ADMIN, raw_user: api_admin_users.CURR_USER) -> list[AnyComponent]:
    sanitized_user = schema.User.admin_model.model_validate(raw_user.model_dump())

    return base_page(
        req,
        c.Heading(text=sanitized_user.username, level=2),
        c.Link(components=[c.Text(text="Back")], on_click=BackEvent()),
        c.Details(
            data=sanitized_user,
            # fields=[
            #     DisplayLookup(field="task_id", title="ID"),
            # ],
        ),
        title=f"User - {sanitized_user.username}",
    )


@base_router.get("/{path:path}")
async def admin_ng_html_landing() -> HTMLResponse:
    return HTMLResponse(prebuilt_html(title="YATB NG admin"))
