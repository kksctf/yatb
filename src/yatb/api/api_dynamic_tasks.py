import datetime
from ipaddress import ip_address
from typing import Annotated, NamedTuple
from uuid import UUID

import humanize
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from yatb import auth, schema
from yatb.config import settings
from yatb.db import TaskDB
from yatb.shared.dtc.client import DynamicTasksEtcdClient, TaskUserPair
from yatb.shared.dtc.models import DynamicTaskInfo, DynamicTaskInfoReady, DynamicTaskQuery, DynamicTaskState
from yatb.utils.log_helper import get_logger

from .utils import CURRENT_TASK

logger = get_logger("api.dynamic_tasks")

router = APIRouter(
    prefix="/dynamic",
    tags=["dynamic_tasks"],
)


class UserTaskPair(NamedTuple):
    user: schema.User
    task: schema.Task

    def t(self) -> TaskUserPair:
        return TaskUserPair(task=self.task.task_id, user=self.user.user_id)


class MultipleInfoRequest(BaseModel):
    tasks: list[UUID]


class MultipleInfoResponse(BaseModel):
    data: dict[UUID, str]


class DynamicTasksClient(DynamicTasksEtcdClient):
    def __init__(self) -> None:
        logger.info("Trying to start dynamic tasks client")

        base_url = settings.DYNAMIC_TASKS_ETCD or "127.0.0.1"
        port = settings.DYNAMIC_TASKS_ETCD_PORT
        # x_token = settings.DYNAMIC_TASKS_CONTROLLER_TOKEN or ""

        super().__init__(
            base_url=base_url,
            port=port,
            # headers={
            #     "X-Token": x_token,
            # },
            # timeout=httpx.Timeout(connect=5.0, read=120.0, write=5.0, pool=5.0),
        )
        logger.info(f"DTC client started with {base_url = }")

    @classmethod
    def format_addr(cls, host: str) -> str:
        try:
            ip = ip_address(host)

            if ip.version == 4:  # noqa: PLR2004
                ip = f"{ip}"
            elif ip.version == 6:  # noqa: PLR2004
                ip = f"[{ip}]"

        except ValueError as ex:
            ip = host

        return ip

    async def format_model_info(self, model: DynamicTaskInfo | None) -> str:
        if not model:
            return "Status: task not started"

        match model.state:
            case DynamicTaskState.PREPARED:
                return "Status: task preparing for build"

            case DynamicTaskState.BUILDING:
                return "Status: task building"

            case DynamicTaskState.READY:
                if not isinstance(model, DynamicTaskInfoReady):
                    raise Exception

                # vpn_info = await self.get_vpn_info(model.user_id)

                ret = ""
                ret += "Status: Running <br>"

                if model.static_link:
                    ret += (
                        "<a class='btn btn-outline-primary btn-sm col-auto m-1 flex-fill' "
                        f"href='{model.static_link}' rel='noopener noreferrer' "
                        f"target='_blank'>Builded task file</a>\n"  # TODO: normal name
                    )

                for hp in model.hps:
                    link = f"http://{self.format_addr(hp.host)}:{hp.port}/"
                    ret += f"<a href='{link}'>{link}</a> <br>"

                # if vpn_info and is_vpninfo_generated(vpn_info):
                #     ret += f"Your task at {vpn_info.netinfo.task_net_task.compressed} <br>"

                now = datetime.datetime.now(tz=datetime.UTC)
                ret += f"Will die after {humanize.precisedelta(model.time_of_death - now)}"

                return ret

            case DynamicTaskState.DELETING:
                return "Status: task deleting"

            case extra:
                return f"Status: {extra!r} FIXME PLEASE"

    async def start(self, handle: UserTaskPair, *, force_rebuild: bool = False) -> str:
        models = await self.get_task_multi_info(handle.user)
        if len(models) != 0 and not handle.user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Too many tasks...",
            )

        if force_rebuild and not handle.user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No no no mister fish!",
            )

        try:
            model = await self.setup_task(task=handle.task, user=handle.user, force_rebuild=force_rebuild)
            return await self.format_model_info(model)
        except TimeoutError as ex:
            return f"Timeout error {ex = }"

    async def stop(self, handle: UserTaskPair):
        status = await self.query_task(handle.t(), DynamicTaskQuery.STOP)
        return f"Status: {status.value = }"  # TODO: fancy this

    async def restart(self, handle: UserTaskPair):
        status = await self.query_task(handle.t(), DynamicTaskQuery.RESTART)
        return f"Status: {status.value = }"  # TODO: fancy this

    async def extend(self, handle: UserTaskPair) -> str:
        status = await self.query_task(handle.t(), DynamicTaskQuery.EXTEND)
        return f"Status: {status.value = }"  # TODO: fancy this

    async def info(self, handle: UserTaskPair) -> str:
        model = await self.get_task_info(handle.t())
        return await self.format_model_info(model)


__client: DynamicTasksClient = DynamicTasksClient()


async def _get_client() -> DynamicTasksClient:
    if not settings.DYNAMIC_TASKS_ETCD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="dynamic tasks not enabled",
        )

    return __client


def get_client_safe() -> DynamicTasksClient | None:
    if not settings.DYNAMIC_TASKS_ETCD:
        return None

    return __client


async def get_dynamic_task(task: CURRENT_TASK) -> TaskDB:
    if not task.dti:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Bad task",
        )
    return task


CLIENT = Annotated[DynamicTasksClient, Depends(_get_client)]
CURRENT_DYNAMIC_TASK = Annotated[TaskDB, Depends(get_dynamic_task)]


@router.get("/start/{task_id}")
async def api_dynamic_task_start(
    user: auth.CURR_USER,
    task: CURRENT_DYNAMIC_TASK,
    client: CLIENT,
    force_rebuild: Annotated[bool, Query()] = False,  # noqa: FBT002
) -> HTMLResponse:
    info = await client.start(UserTaskPair(task=task, user=user), force_rebuild=force_rebuild)
    return HTMLResponse(info)


@router.get("/stop/{task_id}")
async def api_dynamic_task_stop(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT) -> HTMLResponse:
    info = await client.stop(UserTaskPair(task=task, user=user))
    return HTMLResponse(info)


@router.get("/restart/{task_id}")
async def api_dynamic_task_restart(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT) -> HTMLResponse:
    info = await client.restart(UserTaskPair(task=task, user=user))
    return HTMLResponse(info)


@router.get("/extend/{task_id}")
async def api_dynamic_task_extend(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT) -> HTMLResponse:
    info = await client.extend(UserTaskPair(task=task, user=user))
    return HTMLResponse(info)


@router.get("/info/{task_id}")
async def api_dynamic_task_info(user: auth.CURR_USER, task: CURRENT_DYNAMIC_TASK, client: CLIENT) -> HTMLResponse:
    info = await client.info(UserTaskPair(task=task, user=user))
    return HTMLResponse(info)


@router.get("/admin/destroy/{task_id}")
async def api_dynamic_task_admin_destroy(
    user: auth.CURR_ADMIN,
    task: CURRENT_DYNAMIC_TASK,
    client: CLIENT,
) -> str:
    await client.destroy_task(UserTaskPair(task=task, user=user).t())
    return "ok"


@router.post("/info")
async def api_dynamic_task_infos(
    user: auth.CURR_USER,
    client: CLIENT,
    req: MultipleInfoRequest,
) -> MultipleInfoResponse:
    resp = MultipleInfoResponse(data={})

    models = await client.get_task_multi_info(user)

    # TODO: костыль ебаный
    for uuid in req.tasks:
        resp.data[uuid] = await client.format_model_info(None)

    for model in models:
        resp.data[model.task_id] = await client.format_model_info(model)

    return resp


# @router.get("/vpn")
# async def get_vpn(
#     user: auth.CURR_USER,
#     client: CLIENT,
# ) -> PlainTextResponse:
#     state = await client.get_global()
#     if not state:
#         return PlainTextResponse("VPN worker is not ready yet :cry:")

#     info = await client.get_vpn_info(user.user_id)
#     if not info:
#         info = await client.setup_vpn(user)

#     if not is_vpninfo_generated(info):
#         return PlainTextResponse("Generating your personal VPN...")

#     data = ""
#     data += f"""
# [Interface]
# PrivateKey = {info.client.private_key}
# Address = {info.netinfo.client_ip!s}/{settings.VPN_USER_NET_PREFIX}

# [Peer]
# PublicKey = {state.server.public_key}
# AllowedIPs = {info.netinfo.client_ip_with_net(prefix=settings.VPN_USER_NET_PREFIX)!s}, {info.netinfo.task_net!s}
# Endpoint = {settings.VPN_HOST}:{state.port}
#     """.strip()
#     return PlainTextResponse(data)
