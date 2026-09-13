from collections.abc import AsyncIterable
from typing import TypeVar

_T = TypeVar("_T")


async def async_to_list(source: AsyncIterable[_T]) -> list[_T]:
    return [t async for t in source]


async def async_first(source: AsyncIterable[_T]) -> _T:
    async for t in source:
        return t
    raise Exception("not found")
