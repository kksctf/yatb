from typing import Annotated, TypeAlias

from fastapi import Depends, Request


async def is_httpx(req: Request) -> bool:
    return req.headers.get("HX-Request") == "true"


IS_HTTPX: TypeAlias = Annotated[bool, Depends(is_httpx)]
