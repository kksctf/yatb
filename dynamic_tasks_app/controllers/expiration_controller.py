import asyncio
import datetime
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4

from loguru import logger

from ..config import DEFAULT_TTL


@dataclass
class StackInfo:
    id: UUID
    stack: AsyncExitStack
    death_time: datetime.datetime
    death_task: asyncio.Task | None = None

    @staticmethod
    def now() -> datetime.datetime:
        return datetime.datetime.now(tz=datetime.UTC)

    @classmethod
    def build(cls, stack: AsyncExitStack, *, ttl: datetime.timedelta = DEFAULT_TTL) -> Self:
        now = cls.now()
        return cls(
            id=uuid4(),
            stack=stack,
            death_time=now + ttl,
        )

    def extend_life(self, by: datetime.timedelta) -> None:
        self.death_time += by

    async def die(self) -> None:
        await self.stack.aclose()

    @property
    def time_left(self) -> datetime.timedelta:
        now = self.now()
        return self.death_time - now

    @property
    def is_expired(self) -> bool:
        now = self.now()
        return now > self.death_time

    def __repr__(self) -> str:
        return (
            f"StackInfo({self.id = }, death = '{self.death_time}', "
            f"time_left = '{self.time_left}', {self.is_expired = })"
        )


class ExpirationController:
    root_stack: AsyncExitStack
    stacks: dict[UUID, StackInfo]

    def __init__(self) -> None:
        self.root_stack = AsyncExitStack()
        self.stacks = {}

    def get(self, id: UUID) -> StackInfo:
        return self.stacks[id]

    async def push_stack(self, stack: AsyncExitStack) -> StackInfo:
        stack = await self.root_stack.enter_async_context(stack)
        info = StackInfo.build(stack)
        self.stacks[info.id] = info

        await self._create_death_task(info)

        logger.info(f"{info = } created")

        return info

    def extend_life(self, id: UUID, by: datetime.timedelta) -> StackInfo:
        info = self.stacks[id]
        info.extend_life(by)

        logger.info(f"Lifetime of {info = } extended")

        # TODO: recreate death task

        return info

    async def _create_death_task(self, info: StackInfo) -> None:
        async def _task() -> None:
            try:
                await asyncio.sleep(info.time_left.seconds + 1)
            except asyncio.CancelledError:
                logger.info(f"{info = } death task got cancelled")

            if not info.is_expired:
                logger.info(f"{info = } death task finished, but info is fresh, so restaring")
                info.death_task = asyncio.create_task(_task())
                return

            logger.info(f"{info = } is expired")
            await info.die()
            del self.stacks[info.id]
            logger.info(f"{info = } is cleaned")

        info.death_task = asyncio.create_task(_task())

    async def close(self):
        logger.info(f"{len(self.stacks) = } cleaning...")

        await self.root_stack.aclose()

        logger.info(f"{len(self.stacks) = } cleaned")
