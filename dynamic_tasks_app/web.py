from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status

from dynamic_tasks_app.connectors import ExternalDynamicTaskInfo

from .config import settings
from .connectors import DynamicTaskInfo
from .connectors.errors import GenericConnectorError, InstanceNotFoundError
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

from . import view

app.include_router(view.api_rotuer)
app.include_router(view.base_router)


async def check_token(request: Request):
    token = request.headers.get("X-Token", None)
    if token != settings.DYNAMIC_TASKS_CONTROLLER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        )


router = APIRouter(
    prefix="/api",
    tags=["api"],
    dependencies=[
        Depends(check_token),
    ],
)


@asynccontextmanager
async def execption_handler():
    try:
        yield
    except InstanceNotFoundError as ex:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": f"{ex!r}",
            },
        ) from ex
    except GenericConnectorError as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": f"{ex!r}",
            },
        ) from ex
    except NotImplementedError as ex:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
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
async def api_restart(task_info: DynamicTaskInfo) -> ExternalDynamicTaskInfo:
    async with execption_handler():
        return await connector.restart(task_info)


@router.post("/extend")
async def api_extend(task_info: DynamicTaskInfo) -> ExternalDynamicTaskInfo:
    async with execption_handler():
        return await connector.extend(task_info)


@router.post("/info")
async def api_info(task_info: DynamicTaskInfo) -> ExternalDynamicTaskInfo:
    async with execption_handler():
        return await connector.info_task(task_info)


app.include_router(router)
