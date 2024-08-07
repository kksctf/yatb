from collections.abc import Callable
from typing import Annotated, Literal, Self, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from httpx import AsyncClient
from pydantic import BaseModel

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

    @classmethod
    def build(cls, task: schema.Task, user: schema.User) -> Self:
        if not task.dynamic_task_type:
            raise Exception("impossible")

        return cls(
            name=f"{task.task_id}",
            descriptor=task.task_id,
            type=task.dynamic_task_type,
            user_id=f"{user.user_id}",
        )


class DynamicTasksClient(AsyncClient):
    def __init__(self) -> None:
        if not settings.DYNAMIC_TASKS_CONTROLLER_TOKEN:
            return

        self.headers["X-Token"] = settings.DYNAMIC_TASKS_CONTROLLER_TOKEN

    async def start(self, task_info: DynamicTaskInfo):
        pass

    async def stop(self, task_info: DynamicTaskInfo):
        pass

    async def restart(self, task_info: DynamicTaskInfo):
        pass

    async def info(self, task_info: DynamicTaskInfo):
        pass


__client: DynamicTasksClient = DynamicTasksClient()


async def __get_client() -> DynamicTasksClient:
    if not settings.DYNAMIC_TASKS_CONTROLLER or not settings.DYNAMIC_TASKS_CONTROLLER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="dynamic tasks not enabled",
        )
    return __client


async def get_dynamic_task(task: CURRENT_TASK) -> TaskDB:
    if not task.dynamic_task_handle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad task",
        )
    return task


CLIENT = Annotated[DynamicTasksClient, Depends(__get_client)]
CURRENT_DYNAMIC_TASK = Annotated[TaskDB, Depends(get_dynamic_task)]


@router.post("/start/{task_id}")
async def api_dynamic_task_start(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT):
    return await client.start(DynamicTaskInfo.build(task=task, user=user))


@router.post("/stop/{task_id}")
async def api_dynamic_task_stop(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT):
    return await client.stop(DynamicTaskInfo.build(task=task, user=user))


@router.post("/restart/{task_id}")
async def api_dynamic_task_restart(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT):
    return await client.restart(DynamicTaskInfo.build(task=task, user=user))


@router.post("/info/{task_id}")
async def api_dynamic_task_info(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT):
    return await client.info(DynamicTaskInfo.build(task=task, user=user))
