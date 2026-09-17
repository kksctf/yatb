from typing import Annotated

from fastapi import Depends, Request


async def is_httpx(req: Request) -> bool:
    return req.headers.get("HX-Request") == "true"


type IS_HTTPX = Annotated[bool, Depends(is_httpx)]
