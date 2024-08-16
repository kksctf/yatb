import datetime
from collections.abc import Callable
from typing import Annotated, Literal, Self, TypeAlias, cast
from uuid import UUID

import httpx
import humanize
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from httpx import AsyncClient
from pydantic import BaseModel, TypeAdapter

from .. import auth, db, schema
from ..config import settings
from ..db.beanie import TaskDB, UserDB
from ..utils import metrics
from ..utils.log_helper import get_logger
from .api_tasks import CURRENT_TASK

logger = get_logger("api.dynamic_tasks")

router = APIRouter(
    prefix="/dynamic",
    tags=["dynamic_tasks"],
)


class DynamicTaskInfo(BaseModel):
    name: str
    descriptor: UUID

    type: schema.task.DynamicTaskType

    user_id: str

    flag: str

    @classmethod
    def build(cls, task: schema.Task, user: schema.User) -> Self:
        if not task.dynamic_task_info:
            raise Exception("impossible")

        return cls(
            name=f"{task.task_id}",
            descriptor=task.task_id,
            type=task.dynamic_task_info.dynamic_task_type,
            user_id=f"{user.user_id}",
            flag=task.flag.flag_value(user),
        )


class ExternalDynamicTaskInfo(BaseModel):
    class HostPortPair(BaseModel):
        host: str
        port: int

    id: UUID

    task_descriptor: UUID

    user_id: str

    hp: HostPortPair

    least_time: datetime.timedelta


class ExternalDynamicTaskError(BaseModel):
    class Detail(BaseModel):
        error: str

    detail: Detail


_TT: TypeAlias = ExternalDynamicTaskInfo | ExternalDynamicTaskError
ExternalDynamicTaskResp = TypeAdapter[_TT](_TT)


class DynamicTasksClient(AsyncClient):
    def __init__(self) -> None:
        if not settings.DYNAMIC_TASKS_CONTROLLER_TOKEN or not settings.DYNAMIC_TASKS_CONTROLLER:
            return

        super().__init__(
            base_url=settings.DYNAMIC_TASKS_CONTROLLER,
            headers={
                "X-Token": settings.DYNAMIC_TASKS_CONTROLLER_TOKEN,
            },
            timeout=httpx.Timeout(connect=5.0, read=120.0, write=5.0, pool=5.0),
        )

    def format_resp(self, resp: httpx.Response) -> str:
        info = ExternalDynamicTaskResp.validate_json(resp.text)
        return self.format_info(info)

    def format_info(self, info: _TT) -> str:
        if not isinstance(info, ExternalDynamicTaskInfo):
            return f"Status: {info.detail}"

        ret = ""
        ret += "Status: Running <br>"

        try:
            ip = ip_address(info.hp.host)

            if ip.version == 4:
                ip = f"{ip}"
            elif ip.version == 6:
                ip = f"[{ip}]"

        except ValueError as ex:
            ip = info.hp.host

        link = f"http://{ip}:{info.hp.port}/"
        ret += f"<a href='{link}'>{link}</a> <br>"

        ret += f"Will die after {humanize.precisedelta(info.least_time)}"

        return ret

    async def start(self, task_info: DynamicTaskInfo) -> str:
        resp = await self.post("/api/start", json=task_info.model_dump(mode="json"))
        return self.format_resp(resp)

    async def stop(self, task_info: DynamicTaskInfo):
        resp = await self.post("/api/stop", json=task_info.model_dump(mode="json"))

        if resp.status_code == status.HTTP_200_OK:
            return "ok"

        try:
            err = ExternalDynamicTaskError.model_validate_json(resp.text)
        except Exception as ex:
            return "error?"
        else:
            return f"Status: {err.detail}"

    async def restart(self, task_info: DynamicTaskInfo):
        pass

    async def info(self, task_info: DynamicTaskInfo) -> str:
        resp = await self.post("/api/info", json=task_info.model_dump(mode="json"))
        return self.format_resp(resp)


__client: DynamicTasksClient = DynamicTasksClient()


async def __get_client() -> DynamicTasksClient:
    if not settings.DYNAMIC_TASKS_CONTROLLER or not settings.DYNAMIC_TASKS_CONTROLLER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="dynamic tasks not enabled",
        )
    return __client


async def get_dynamic_task(task: CURRENT_TASK) -> TaskDB:
    if not task.dynamic_task_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad task",
        )
    return task


CLIENT = Annotated[DynamicTasksClient, Depends(__get_client)]
CURRENT_DYNAMIC_TASK = Annotated[TaskDB, Depends(get_dynamic_task)]


@router.get("/start/{task_id}")
async def api_dynamic_task_start(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT) -> HTMLResponse:
    info = await client.start(DynamicTaskInfo.build(task=task, user=user))
    return HTMLResponse(info)


@router.get("/stop/{task_id}")
async def api_dynamic_task_stop(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT) -> HTMLResponse:
    info = await client.stop(DynamicTaskInfo.build(task=task, user=user))
    return HTMLResponse(info)


@router.get("/restart/{task_id}")
async def api_dynamic_task_restart(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT) -> HTMLResponse:
    info = await client.restart(DynamicTaskInfo.build(task=task, user=user))
    return HTMLResponse(info)


@router.get("/info/{task_id}")
async def api_dynamic_task_info(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT) -> HTMLResponse:
    info = await client.info(DynamicTaskInfo.build(task=task, user=user))
    return HTMLResponse(info)
