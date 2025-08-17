import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastui import AnyComponent, FastUI, prebuilt_html
from fastui import components as c
from fastui.components.display import DisplayLookup
from fastui.events import BackEvent, GoToEvent
from pydantic import BaseModel

from .config import settings
from .controllers.ports_controller import HostPortPair
from .web import connector

sec = HTTPBasic()


async def check_sec(credentials: Annotated[HTTPBasicCredentials, Depends(sec)]) -> None:
    exc = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="no",
        headers={"WWW-Authenticate": "Basic"},
    )

    if settings.DEBUG:
        return

    if credentials.username != "admin":
        raise exc

    if credentials.password != settings.ADMIN_PASSWORD:
        raise exc


base_router = APIRouter(
    prefix="/admin",
    tags=["admin-ng"],
    dependencies=[Depends(check_sec)],
)

api_rotuer = APIRouter(
    prefix="/api/admin",
    tags=["admin-ng-api"],
    dependencies=[Depends(check_sec)],
)


class ServiceInfo(BaseModel):
    lti_id: uuid.UUID

    task_id: uuid.UUID
    user_id: str  # usually UUID

    flag: str

    expiration_id: uuid.UUID | None
    expiration_date: datetime | None
    expiration_time: timedelta | None

    ports: list[HostPortPair]

    def key(self) -> tuple[uuid.UUID, str]:
        return (self.task_id, self.user_id)


async def get_services() -> list[ServiceInfo]:
    ret: list[ServiceInfo] = []
    
    return ret

    for (task_id, user_id), task in connector.ltis.items():
        if task.expiration_id:
            expiration_info = await connector.expiration_controller.get(
                task.expiration_id,
            )
            death_time = expiration_info.death_time
            time_left = expiration_info.time_left
        else:
            death_time = None
            time_left = None

        ret.append(
            ServiceInfo(
                lti_id=task.id,
                task_id=task_id,
                user_id=user_id,
                flag=task.flag,
                expiration_id=task.expiration_id,
                expiration_date=death_time,
                expiration_time=time_left,
                ports=task.ports_env.tracking_ports if task.ports_env else [],
            ),
        )

    return ret


def url_gen(req: Request, path: str) -> str:
    return str(req.url_for("admin_ng_html_landing", path=path))


def base_page(req: Request, *components: AnyComponent, title: str | None = None) -> list[AnyComponent]:
    return [
        c.PageTitle(text=f"DTC Admin — {title if title else 'Root'}"),
        c.Navbar(
            title="DTC Admin",
            title_event=GoToEvent(url=url_gen(req, "")),
            start_links=[
                c.Link(
                    components=[c.Text(text="Services")],
                    on_click=GoToEvent(url=url_gen(req, "services")),
                    active="startswith:/services",
                ),
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
async def admin_ng_index(req: Request) -> list[AnyComponent]:
    return base_page(req, c.Text(text="..."))


@api_rotuer.get("/services", response_model=FastUI, response_model_exclude_none=True)
async def admin_ng_services(req: Request) -> list[AnyComponent]:
    services = await get_services()
    data = sorted(services, key=lambda iv: iv.key())
    return base_page(
        req,
        c.Table(
            data=data,
            data_model=ServiceInfo,
            columns=[
                DisplayLookup(field="lti_id", title="ID", on_click=GoToEvent(url=url_gen(req, "service/{lti_id}"))),
                DisplayLookup(field="task_id", title="TaskID"),
                DisplayLookup(field="user_id", title="UserID"),
                DisplayLookup(field="flag", title="Flag"),
                # DisplayLookup(field="expiration_id", title="ExpID"),
                DisplayLookup(field="expiration_date", title="Death at"),
                DisplayLookup(field="expiration_time", title="After"),
                DisplayLookup(field="ports", title="Ports"),
            ],
        ),
        title="Tasks",
    )


@api_rotuer.get("/service/{service_id}", response_model=FastUI, response_model_exclude_none=True)
async def admin_ng_service(req: Request, service_id: uuid.UUID) -> list[AnyComponent]:
    services = await get_services()
    for service in services:
        if service.lti_id == service_id:
            break
    else:
        raise Exception

    return base_page(
        req,
        c.Heading(text=f"{service.lti_id}", level=2),
        c.Link(components=[c.Text(text="Back")], on_click=BackEvent()),
        c.Details(
            data=service,
            # fields=[
            #     DisplayLookup(field="task_id", title="ID"),
            # ],
        ),
        title=f"Service - {service.lti_id}",
    )


# should be the last


@base_router.get("/{path:path}")
async def admin_ng_html_landing() -> HTMLResponse:
    return HTMLResponse(prebuilt_html(title="DTC admin.."))
