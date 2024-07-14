from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from .config import settings
from .connectors import DynamicTaskInfo
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
)

# TODO: token check
router = APIRouter(
    prefix="/api",
    tags=["api"],
)


@router.post("/start")
async def api_start(task_info: DynamicTaskInfo):
    return await connector.start(task_info)


@router.post("/stop")
async def api_stop(task_info: DynamicTaskInfo):
    return await connector.stop(task_info)


@router.post("/restart")
async def api_restart(task_info: DynamicTaskInfo):
    return await connector.restart(task_info)


@router.post("/info")
async def api_info(task_info: DynamicTaskInfo):
    return await connector.info(task_info)
