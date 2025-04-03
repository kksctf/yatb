from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger
from miniopy_async import Minio

from .config import settings

s3 = Minio(
    endpoint=settings.s3_endpoint,
    access_key=settings.S3_ACCESS,
    secret_key=settings.S3_SECRET,
    secure=False,  # http for False, https for True
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not await s3.bucket_exists(settings.BUILD_RESULT_BUCKET_NAME):
        await s3.make_bucket(settings.BUILD_RESULT_BUCKET_NAME)

    try:
        yield
    finally:
        pass


app = FastAPI(
    lifespan=lifespan,
    #     middleware=[process_exception],
)


@app.get("/{user_key}/{task_key}/{file_name}")
async def get_file(user_key: str, task_key: str, file_name: str) -> StreamingResponse:
    object_name = f"{user_key}/{task_key}/{file_name}"

    try:
        info = await s3.stat_object(settings.BUILD_RESULT_BUCKET_NAME, object_name)
        logger.info(f"{object_name = } -> {info = }")
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Some error: {ex!r}",
        ) from ex

    async def stream() -> AsyncGenerator[bytes, Any]:
        async with aiohttp.ClientSession() as session:
            response = await s3.get_object(
                settings.BUILD_RESULT_BUCKET_NAME,
                object_name,
                session,
            )

            if not response:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No response",
                )

            async for data, _ in response.content.iter_chunks():
                yield data

    return StreamingResponse(stream())
