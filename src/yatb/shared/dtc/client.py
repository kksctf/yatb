import asyncio
from collections.abc import AsyncGenerator, Container, Sequence
from dataclasses import dataclass
from typing import NamedTuple, Self
from uuid import UUID

from aetcd import Client, Event, EventKind
from loguru import logger

from yatb import schema

from .models import (
    DynamicTaskInfo,
    DynamicTaskInfoBase,
    DynamicTaskInfoBuilding,
    DynamicTaskInfoDeleting,
    DynamicTaskInfoModel,
    DynamicTaskInfoReady,
    DynamicTaskQuery,
    DynamicTaskQueryStatus,
    DynamicTaskState,
    VPNGlobalState,
    VPNUserInfo,
    VPNUserInfoBase,
    VPNUserInfoGenerated,
    VPNUserInfoModel,
)


class TaskUserPair(NamedTuple):
    task: UUID
    user: UUID


@dataclass
class TaskWatchEvent:
    raw_event: Event
    model: DynamicTaskInfo
    prev_model: DynamicTaskInfo | None


@dataclass
class TaskRPCEvent(TaskWatchEvent):
    rpc_action: DynamicTaskQuery


@dataclass
class VPNWatchEvent:
    raw_event: Event
    model: VPNUserInfo
    prev_model: VPNUserInfo | None


class ExtendedClient(Client):
    pass


class _DynamicTasksEtcdClientBase:
    _client: ExtendedClient
    root_prefix: str = "/dtc"

    def __init__(self, base_url: str, port: int) -> None:
        self._client = ExtendedClient(
            host=base_url,
            port=port,
        )

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs) -> bool | None:
        return await self._client.__aexit__(*args, **kwargs)


class _DynamicTasksEtcdClientTasks(_DynamicTasksEtcdClientBase):
    tasks_prefix: str = f"{_DynamicTasksEtcdClientBase.root_prefix}/tasks"

    @classmethod
    def _task_user_key(cls, user: UUID) -> bytes:
        return f"{cls.tasks_prefix}/u:{user!s}".encode()

    @classmethod
    def _full_task_key(cls, task: UUID, user: UUID, *, rpc: bool = False) -> bytes:
        base = cls._task_user_key(user) + f"/t:{task!s}".encode()

        if rpc:
            base += b"/rpc"

        return base

    @classmethod
    def _full_task_key_h(cls, handle: TaskUserPair, *, rpc: bool = False) -> bytes:
        return cls._full_task_key(task=handle.task, user=handle.user, rpc=rpc)

    @classmethod
    def _full_task_key_m(cls, model: DynamicTaskInfo, *, rpc: bool = False) -> bytes:
        return cls._full_task_key(task=model.task_id, user=model.user_id, rpc=rpc)

    @classmethod
    def _task_bytes_to_model(cls, data: bytes, extra: str = "") -> DynamicTaskInfo:
        try:
            root_model = DynamicTaskInfoModel.model_validate_json(data)
        except Exception as ex:  # FIXME: ...
            logger.warning(f"Error validation dtinfo model: {ex = } for {extra}")
            raise

        return root_model.root

    async def get_task_info(self, handle: TaskUserPair) -> DynamicTaskInfo | None:
        value = await self._client.get(self._full_task_key_h(handle))
        if not value:
            return None

        return self._task_bytes_to_model(value.value, f"{handle = }")

    async def get_task_multi_info(self, user: schema.User) -> list[DynamicTaskInfo]:
        values = await self._client.get_prefix(self._task_user_key(user.user_id))

        return [
            self._task_bytes_to_model(
                value.value,
                f"multi for {user.short_desc() = }",
            )
            for value in values
            if not value.key.endswith(b"/rpc")
        ]

    async def watch_for(
        self,
        key: bytes,
        states: Container[DynamicTaskState],
        ready_event: asyncio.Event,
    ) -> DynamicTaskInfo:
        # TODO: maybe handle DELETE event?)

        if not self._client._watcher:
            raise Exception

        event_queue = asyncio.Queue()

        watcher_callback = await self._client._watcher.add_callback(
            key,
            event_queue.put,
            range_end=None,
            start_revision=None,
            progress_notify=False,
            kind=None,
            prev_kv=False,
            watch_id=None,
            fragment=False,
        )

        ready_event.set()

        try:
            while True:
                event: Event = await asyncio.wait_for(event_queue.get(), None)
                model = self._task_bytes_to_model(event.kv.value, f"{key = }")
                if model.state in states:
                    return model
        finally:
            await self._client._watcher.cancel(watcher_callback.watch_id)  # pyright: ignore[reportArgumentType]

    async def setup_task(self, task: schema.Task, user: schema.User) -> DynamicTaskInfo:
        model = DynamicTaskInfoBase.build(task=task, user=user)
        key = self._full_task_key_h(TaskUserPair(task.task_id, user.user_id))

        watcher_ready = asyncio.Event()
        watcher = asyncio.create_task(
            self.watch_for(
                key,
                states={
                    # DynamicTaskState.BUILDING,
                    DynamicTaskState.READY,
                },
                ready_event=watcher_ready,
            ),
        )
        await watcher_ready.wait()

        await self._client.put(key, model.make_binary())

        return await asyncio.wait_for(watcher, 30)

    async def query_task(self, handle: TaskUserPair, query: DynamicTaskQuery) -> DynamicTaskQueryStatus:
        if not await self._client.get(self._full_task_key_h(handle)):  # TODO: make this check better
            return DynamicTaskQueryStatus.TASK_NOT_FOUND

        rpc = self._full_task_key_h(handle, rpc=True)

        # check for existing operation
        if operation := await self._client.get(rpc):
            # if we requesting the same operation - exit :D
            if DynamicTaskQuery(operation.value.decode()) == query:
                return DynamicTaskQueryStatus.ALREADY_IN_PROGRESS

            # if here - wait for clean
            logger.info(f"Waiting for ending {operation = } on {rpc = }")

            async with asyncio.timeout(delay=30):  # 30s
                async for event in await self._client.watch(rpc):  # TODO: handle infinite loop
                    event: Event
                    if event.kind == EventKind.DELETE:
                        break

        # query new
        await self._client.put(rpc, query.encode())

        return DynamicTaskQueryStatus.REQUESTED

    async def ack_query_task(self, event: TaskRPCEvent) -> None:
        await self._client.delete(event.raw_event.kv.key)

    async def make_task_building(self, model: DynamicTaskInfoBase) -> DynamicTaskInfoBuilding:
        new_model = DynamicTaskInfoBuilding(**model.model_dump(exclude={"state"}))
        await self._client.put(self._full_task_key_m(new_model), new_model.make_binary())
        return new_model

    async def make_task_ready(self, model: DynamicTaskInfoBuilding) -> DynamicTaskInfoReady:
        new_model = DynamicTaskInfoReady(**model.model_dump(exclude={"state"}))
        await self._client.put(self._full_task_key_m(new_model), new_model.make_binary())
        return new_model

    async def task_model_update(self, model: DynamicTaskInfoReady) -> DynamicTaskInfoReady:
        await self._client.put(self._full_task_key_m(model), model.make_binary())
        return model

    async def make_task_deleting(self, model: DynamicTaskInfoReady) -> DynamicTaskInfoReady:
        new_model = DynamicTaskInfoDeleting(**model.model_dump(exclude={"state"}))
        await self._client.put(self._full_task_key_m(new_model), new_model.make_binary())
        return new_model

    async def delete_task(self, model: DynamicTaskInfoDeleting) -> None:
        await self._client.delete(self._full_task_key_m(model))

    async def destroy_task(self, handle: TaskUserPair) -> None:
        await self._client.delete_prefix(self._full_task_key_h(handle))

    async def watch_tasks(self) -> AsyncGenerator[TaskWatchEvent | TaskRPCEvent, None]:
        try:
            async for event in await self._client.watch_prefix(self.tasks_prefix.encode(), prev_kv=True):
                event: Event
                if event.kind != EventKind.PUT:
                    continue

                if event.kv.key.endswith(b"/rpc"):
                    data = await self._client.get(event.kv.key.removesuffix(b"/rpc"))
                    if not data:
                        logger.error(f"{event.kv.key = } no model: {data = }")
                        continue

                    kv = data
                    prev_kv = None

                    rpc = DynamicTaskQuery(event.kv.value.decode())
                else:
                    kv = event.kv
                    prev_kv = event.prev_kv

                model = self._task_bytes_to_model(kv.value, extra=f"watch, {kv.key = }")
                prev_model = (
                    self._task_bytes_to_model(
                        prev_kv.value,
                        f"watch, pre {kv.key = }",
                    )
                    if prev_kv and prev_kv.value
                    else None
                )

                if event.kv.key.endswith(b"/rpc"):
                    yield TaskRPCEvent(
                        event,
                        model,
                        prev_model,
                        rpc_action=rpc,  # pyright: ignore[reportPossiblyUnboundVariable] # it's hard to track ifs
                    )
                else:
                    yield TaskWatchEvent(event, model, prev_model)
        except asyncio.CancelledError as ex:
            logger.info(f"Watcher cancelled with {ex = }")


class _DynamicTasksEtcdClientVPNs(_DynamicTasksEtcdClientBase):
    vpns_prefix: str = f"{_DynamicTasksEtcdClientBase.root_prefix}/vpns"

    @classmethod
    def _vpn_user_key(cls, user: UUID) -> bytes:
        return f"{cls.vpns_prefix}/u:{user!s}".encode()

    @classmethod
    def _vpn_user_key_m(cls, model: VPNUserInfo) -> bytes:
        return cls._vpn_user_key(model.user_id)

    @classmethod
    def _vpn_bytes_to_model(cls, data: bytes, extra: str = "") -> VPNUserInfo:
        try:
            root_model = VPNUserInfoModel.model_validate_json(data)
        except Exception as ex:  # FIXME: ...
            logger.warning(f"Error validation vpn info model: {ex = } for {extra}")
            raise

        return root_model.root

    async def get_vpn_info(self, handle: UUID) -> VPNUserInfo | None:
        value = await self._client.get(self._vpn_user_key(handle))
        if not value:
            return None

        return self._vpn_bytes_to_model(value.value, f"{handle = }")

    async def setup_vpn(self, user: schema.User) -> VPNUserInfo:
        model = VPNUserInfoBase.build(user=user)
        key = self._vpn_user_key(user=user.user_id)

        await self._client.put(key, model.make_binary())

        # TODO: hangs everything...
        event: Event = await self._client.watch_once(key)  # TODO: maybe handle DELETE event?)

        return self._vpn_bytes_to_model(event.kv.value, f"{key = }")

    async def make_vpn_generated(self, model: VPNUserInfoBase) -> VPNUserInfoGenerated:
        new_model = VPNUserInfoGenerated(**model.model_dump(exclude={"state"}))
        await self._client.put(self._vpn_user_key_m(new_model), new_model.make_binary())
        return new_model

    async def save_vpn(self, model: VPNUserInfoGenerated) -> VPNUserInfoGenerated:
        await self._client.put(self._vpn_user_key_m(model), model.make_binary())
        return model

    async def watch_vpns(self) -> AsyncGenerator[VPNWatchEvent, None]:
        try:
            async for event in await self._client.watch_prefix(f"{self.vpns_prefix}/u".encode(), prev_kv=True):
                event: Event
                if event.kind != EventKind.PUT:
                    continue

                kv = event.kv
                prev_kv = event.prev_kv

                model = self._vpn_bytes_to_model(kv.value, extra=f"watch, {kv.key = }")
                prev_model = (
                    self._vpn_bytes_to_model(
                        prev_kv.value,
                        f"watch, pre {kv.key = }",
                    )
                    if prev_kv and prev_kv.value
                    else None
                )

                yield VPNWatchEvent(event, model, prev_model)
        except asyncio.CancelledError as ex:
            logger.info(f"Watcher cancelled with {ex = }")

    async def get_all_vpns(self) -> dict[UUID, VPNUserInfoGenerated]:
        r = await self._client.get_prefix(f"{self.vpns_prefix}/u".encode())
        ret = {}
        for kv in r:
            model = self._vpn_bytes_to_model(kv.value, extra=f"get_all_vpns, {kv.key = }")
            ret[model.user_id] = model
        return ret

    async def get_global(self) -> VPNGlobalState | None:
        value = await self._client.get(f"{self.vpns_prefix}/global".encode())
        if not value:
            return None

        return VPNGlobalState.model_validate_json(value.value)

    async def set_global(self, state: VPNGlobalState) -> None:
        await self._client.put(f"{self.vpns_prefix}/global".encode(), state.make_binary())


class DynamicTasksEtcdClient(_DynamicTasksEtcdClientTasks, _DynamicTasksEtcdClientBase):
    pass
