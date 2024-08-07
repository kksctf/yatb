from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Request, status

from dynamic_tasks_app.connectors import ExternalDynamicTaskInfo

from .config import settings
from .connectors import DynamicTaskInfo, GenericConnectorError
from .connectors.kub import KubeConnector

# WTF: tmp for dev
connector = KubeConnector()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connector.init()
    try:
        yield
    finally:
        await connector.close()


app = FastAPI(
    lifespan=lifespan,
    #     middleware=[process_exception],
)


# TODO: token check
router = APIRouter(
    prefix="/api",
    tags=["api"],
)


@asynccontextmanager
async def execption_handler():
    try:
        yield
    except GenericConnectorError as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": f"{ex!r}",
            },
        ) from ex


@router.post("/start")
async def api_start(task_info: DynamicTaskInfo) -> ExternalDynamicTaskInfo:
    async with execption_handler():
        return await connector.start(task_info)


@router.post("/stop")
async def api_stop(task_info: DynamicTaskInfo):
    async with execption_handler():
        return await connector.stop(task_info)


@router.post("/restart")
async def api_restart(task_info: DynamicTaskInfo):
    async with execption_handler():
        return await connector.restart(task_info)


@router.post("/extend")
async def api_extend(task_info: DynamicTaskInfo):
    async with execption_handler():
        return await connector.extend(task_info)


@router.post("/info")
async def api_info(task_info: DynamicTaskInfo) -> ExternalDynamicTaskInfo:
    async with execption_handler():
        return await connector.info_task(task_info)


app.include_router(router)
