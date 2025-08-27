import asyncio
import datetime
import hashlib
import typing
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel

from yatb.shared.dtc.client import DynamicTasksEtcdClient, TaskRPCEvent, TaskWatchEvent
from yatb.shared.dtc.models import (
    DynamicTaskFeatures,
    DynamicTaskInfo,
    DynamicTaskInfoBase,
    DynamicTaskInfoBuilding,
    DynamicTaskInfoReady,
    DynamicTaskQuery,
    DynamicTaskState,
    HostPortPair,
    VPNGlobalState,
    VPNUserInfoGenerated,
    is_taskinfo_building,
    is_taskinfo_deleting,
    is_taskinfo_prepared,
    is_taskinfo_ready,
    is_vpninfo_generated,
)

from ..config import settings
from ..controllers import ExpirationController, PortsController
from ..controllers.ports_controller import PortsEnv
from .errors import GenericConnectorError, InstanceNotFoundError


@dataclass
class LocalTaskInfo:
    exit_stack: AsyncExitStack
    ports_env: PortsEnv

    @staticmethod
    @lru_cache(maxsize=128)
    def devire_static_random_seq(source: str) -> str:
        # FIXME: wtf this is it...
        return hashlib.sha512(b"o4i765vob347t5v" + source.encode() + b"p3v85yb345yvb345").hexdigest()[:16]


class BaseConnector(ABC):
    etcd: DynamicTasksEtcdClient

    lti_lock: asyncio.Lock
    ltis: dict[tuple[UUID, UUID], LocalTaskInfo]

    expiration_controller: ExpirationController
    ports_controller: PortsController

    run_workers: bool = True
    jobs: asyncio.PriorityQueue[typing.Coroutine]
    workers: list[asyncio.Task[None]]

    watcher_task: asyncio.Task[None]

    _PASSIVE: bool = False

    def __init__(
        self,
        expiration_controller: ExpirationController,
        ports_controller: PortsController,
        *,
        run_workers: bool = settings.DO_WORK,
    ) -> None:
        super().__init__()

        self.lti_lock = asyncio.Lock()
        self.ltis = {}

        self.expiration_controller = expiration_controller
        self.ports_controller = ports_controller

        self.run_workers = run_workers
        self.jobs = asyncio.PriorityQueue()
        self.workers = []

        self.etcd = DynamicTasksEtcdClient(settings.DYNAMIC_TASKS_ETCD, port=settings.DYNAMIC_TASKS_ETCD_PORT)

    async def __aenter__(self) -> Self:
        await self.init()
        await self.etcd.__aenter__()

        if self.run_workers:
            for _ in range(settings.ASYNC_WORKERS_COUNT):
                self.workers.append(asyncio.create_task(self.worker()))

            self.watcher_task = asyncio.create_task(self.watcher())

            logger.info(f"{len(self.workers) = } created")

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.etcd.__aexit__()
        await self.close()

    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        if self.run_workers:
            for worker in self.workers:
                worker.cancel("stopping")
                await worker

            self.watcher_task.cancel("stopping")
            await self.watcher_task

        # logger.critical(f"Closing ports_controller")
        await self.ports_controller.close()
        # logger.critical(f"Closed ports_controller, Closing expiration_controller")
        await self.expiration_controller.close()
        # logger.critical(f"Closed expiration_controller")

    @abstractmethod
    async def _start(
        self,
        task_info: DynamicTaskInfoBuilding,
        lti: LocalTaskInfo,
    ) -> None:
        raise NotImplementedError

    async def _start_vm(
        self,
        task_info: DynamicTaskInfoBuilding,
        lti: LocalTaskInfo,
    ):
        raise NotImplementedError

    @abstractmethod
    async def _build(self, task_info: DynamicTaskInfoBuilding, lti: LocalTaskInfo) -> str:
        raise NotImplementedError

    async def _stop(self, task_info: DynamicTaskInfo) -> None:
        # if not (is_taskinfo_ready(task_info) or is_taskinfo_deleting(task_info)):
        #     raise GenericConnectorError("Task is not initialized yet or not deleting")

        if is_taskinfo_ready(task_info):
            logger.error(f"WTF task info ready?? {task_info = }")

        if is_taskinfo_ready(task_info) or is_taskinfo_deleting(task_info):
            try:
                expiration_stack_info = await self.expiration_controller.get(task_info.expiration_id)

                if task := expiration_stack_info.death_task:
                    task.cancel()

                await self.expiration_controller.kill(expiration_stack_info)
            except KeyError as ex:
                logger.error(f"No expiration container for {task_info = }")
        else:  # elif is_taskinfo_building(task_info):
            try:
                lti = await self.get_lti(task_info)
                await lti.exit_stack.aclose()
            except InstanceNotFoundError:
                logger.warning(f"No lti for {task_info = } on deleting, but seems ok???")

        try:
            await self.etcd.delete_task(task_info)  # type: ignore # FIXME: shit
        except Exception as ex:
            logger.exception(f"{task_info = } double del maybe")

    async def _restart(self, task_info: DynamicTaskInfo):
        await self._stop(task_info)
        return await self.start(task_info)

    async def worker(self) -> None:
        while True:
            try:
                job = await self.jobs.get()
            except asyncio.CancelledError as ex:
                logger.info(f"{ex = }")
                break

            try:
                await job
                self.jobs.task_done()
            except Exception as ex:
                logger.exception("wtf")

    async def handle_event(self, event: TaskWatchEvent) -> None:
        match event.model.state:
            case DynamicTaskState.PREPARED:
                await self.jobs.put(self.start(event.model))

    async def handle_rpc_event(self, event: TaskRPCEvent) -> None:
        match event.rpc_action:
            case DynamicTaskQuery.EXTEND:
                if not is_taskinfo_ready(event.model):
                    return
                await self.jobs.put(self.extend(event.model))
            case DynamicTaskQuery.RESTART:
                if not is_taskinfo_ready(event.model):
                    return
                await self.jobs.put(self.restart(event.model))
            case DynamicTaskQuery.STOP:
                await self.jobs.put(self.stop(event.model))  # type: ignore # FIXME: shit

        # TODO: hmmm возможно надо делать не тут
        await self.etcd.ack_query_task(event)

    async def watcher(self) -> None:
        async for event in self.etcd.watch_tasks():
            logger.debug(f"Got {event = }")

            try:
                if isinstance(event, TaskRPCEvent):
                    await self.handle_rpc_event(event)
                else:
                    await self.handle_event(event)
            except Exception as ex:
                logger.warning(f"{ex = } for {event = }")

    async def init_lti(self, task_info: DynamicTaskInfo) -> LocalTaskInfo:
        async with self.lti_lock:
            if not task_info.user_admin:
                counter = 0
                for _, user_id in self.ltis:
                    if task_info.user_id == user_id:
                        counter += 1

                if counter > 0:
                    raise GenericConnectorError(
                        f"Stop other tasks before running another one, you have {counter = } tasks running",
                    )

            k = (task_info.task_id, task_info.user_id)

            if k in self.ltis:
                raise GenericConnectorError("This task for your team already exsits")

            exit_stack = AsyncExitStack()
            self.ltis[k] = LocalTaskInfo(
                exit_stack=exit_stack,
                ports_env=await exit_stack.enter_async_context(self.ports_controller.get_env()),
            )

            return self.ltis[k]

    async def get_lti(self, task_info: DynamicTaskInfo) -> LocalTaskInfo:
        return await self.get_lti_raw_key((task_info.task_id, task_info.user_id))

    async def get_lti_raw_key(self, key: tuple[UUID, UUID]) -> LocalTaskInfo:
        async with self.lti_lock:
            if key not in self.ltis:
                raise InstanceNotFoundError("No task found")

            return self.ltis[key]

    def free_lti(self, task_info: DynamicTaskInfo) -> None:
        # since this is sync method, we can do not lock
        assert not self.lti_lock.locked()

        k = (task_info.task_id, task_info.user_id)

        if k not in self.ltis:
            logger.warning(f"WTF no {k = } in tasks index while deliting (possible doublefree)")
            return

        del self.ltis[k]

    async def start(self, task_info: DynamicTaskInfoBase) -> DynamicTaskInfoReady:
        async def _x():
            await self.etcd.delete_task(task_info)  # pyright: ignore[reportArgumentType]

        lti = await self.init_lti(task_info)
        lti.exit_stack.callback(lambda: self.free_lti(task_info))
        lti.exit_stack.push_async_callback(_x)  # WTF: :thonk:

        task_info = await self.etcd.make_task_building(task_info)

        try:
            for feature in task_info.features:
                match feature:
                    case DynamicTaskFeatures.SERVICE:
                        await self._start(task_info, lti)
                    case DynamicTaskFeatures.VM:
                        await self._start_vm(task_info, lti)
                    case DynamicTaskFeatures.BUILDER:
                        task_info.static_link = await self._build(task_info, lti)
        except Exception as ex:
            logger.error(f"Got {ex!r} while building or running {task_info = }")
            await lti.exit_stack.aclose()
            raise GenericConnectorError("Something went wrong ;(") from ex
        else:
            tracker = await self.expiration_controller.push_stack(lti.exit_stack)
            logger.info(f"Pushed {tracker = }")

            task_info.expiration_id = tracker.id
            task_info.time_of_death = tracker.death_time

            task_info.hps = [HostPortPair(host=i.host, port=i.port) for i in lti.ports_env.tracking_ports]

            task_info = await self.etcd.make_task_ready(task_info)

            return task_info

    async def stop(self, task_info: DynamicTaskInfoReady) -> None:
        try:
            task_info = await self.etcd.make_task_deleting(task_info)
        except Exception as ex:
            logger.warning(f"unable to make deleting task from {task_info = }, {ex = }")

        await self._stop(task_info)

    async def restart(self, task_info: DynamicTaskInfoReady):
        return await self._restart(task_info)

    async def extend(self, task_info: DynamicTaskInfoReady) -> None:
        tracker = await self.expiration_controller.extend_life(task_info.expiration_id, datetime.timedelta(hours=1))
        task_info.time_of_death = tracker.death_time
        await self.etcd.task_model_update(task_info)
