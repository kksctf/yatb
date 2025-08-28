#!/usr/bin/env python3
# just a very simple builder

import asyncio
from pathlib import Path

import rich.console
from cyclopts import App
from cyclopts.config import Env
from miniopy_async import Minio
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    FLAG: str
    RANDOM_STRING_SEQ: str
    
    EXPORT_PATH: Path

    S3_HOST: str
    S3_PORT: int = 80
    S3_ACCESS: str
    S3_SECRET: str

    BUILD_RESULT_BUCKET_NAME: str

    @property
    def s3_endpoint(self) -> str:
        return f"{self.S3_HOST}:{self.S3_PORT}"


settings = Settings()  # type: ignore

app = App(
    name="Task building manager",
    config=Env(""),
)
c = rich.console.Console()


@app.command()
async def upload(name: str):
    s3 = Minio(
        endpoint=settings.s3_endpoint,
        access_key=settings.S3_ACCESS,
        secret_key=settings.S3_SECRET,
        secure=False,  # http for False, https for True
    )
    c.print(f"Uploading artifact with {settings = } as {name = }")

    files = list(settings.EXPORT_PATH.glob("*"))
    c.print(f"Files: {files}")

    for file in files:
        fname = f"{name}/{file.name}"
        c.print(f"{fname!r} found")
        with file.open("rb") as f:
            await s3.put_object(
                settings.BUILD_RESULT_BUCKET_NAME,
                fname,
                f,
                length=file.stat().st_size,
            )
        c.print(f"{fname!r} uploaded")

    await asyncio.sleep(3)  # k8s moment. так надо.


if __name__ == "__main__":
    app()
