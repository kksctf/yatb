from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger

from .client import MinioEx
from .config import settings

s3: MinioEx


@asynccontextmanager
async def lifespan(app: FastAPI):
    global s3
    s3 = MinioEx()
    await s3.setup_buckets()

    logger.info("Init ok")

    try:
        yield
    finally:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/shared/{task_key}/{file_name}")
async def get_public_file(task_key: str, file_name: str) -> StreamingResponse:
    object_name = f"{task_key}/{file_name}"

    try:
        info = await s3.stat_object(settings.STATIC_BUCKET_NAME, object_name)
        logger.info(f"{object_name = } -> {info = }")
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Some error: {ex!r}",
        ) from ex

    async def stream() -> AsyncGenerator[bytes, Any]:
        response = await s3.get_object(
            settings.STATIC_BUCKET_NAME,
            object_name,
            session=None,  # this handled by MinioEx
        )

        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No response",
            )

        async for data, _ in response.content.iter_chunks():
            yield data

    return StreamingResponse(stream())


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
        response = await s3.get_object(
            settings.BUILD_RESULT_BUCKET_NAME,
            object_name,
            session=None,  # this handled by MinioEx
        )

        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No response",
            )

        async for data, _ in response.content.iter_chunks():
            yield data

    return StreamingResponse(stream())
