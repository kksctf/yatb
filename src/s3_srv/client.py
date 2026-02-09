import hashlib
import io
import tarfile
from collections.abc import Sequence
from gzip import GzipFile
from pathlib import Path
from typing import IO, BinaryIO, cast

import aiohttp
from loguru import logger
from miniopy_async import Minio, S3Error

from .config import settings


class MinioEx(Minio):
    s3client: aiohttp.ClientSession

    async def setup_buckets(
        self,
        buckets: Sequence[str] = [
            settings.STATIC_BUCKET_NAME,
            settings.TASKS_BUCKET_NAME,
            settings.BUILD_RESULT_BUCKET_NAME,
        ],
    ) -> None:
        for bucket in buckets:
            if await self.bucket_exists(bucket):
                continue
            await self.make_bucket(bucket, location=settings.S3_REGION or "us-east-1")
            logger.info(f"Created s3 {bucket = }")

    async def upload_directory(
        self,
        source: Path,
        bucket_name: str,
        object_name: str,
        *,
        ignore_cache: bool = False,
    ) -> str:
        assert source.is_absolute()
        assert source.is_dir()

        with io.BytesIO() as buff:
            with (
                # have to separately create gzip, because we need to setup mtime=0
                GzipFile(fileobj=buff, mode="wb", mtime=0) as gzip,
                tarfile.open(
                    # https://stackoverflow.com/a/58407810
                    fileobj=cast("IO[bytes]", gzip),  # IDK WHY, but for some reason gzip is not IO[bytes]...
                    mode="w|",
                ) as tar,
            ):
                for file in source.iterdir():
                    tar.add(file, arcname=file.relative_to(source))  # string absolute long path
            buff.seek(0)  # reset to 0. because... you knew.

            # calc tar hash and check whenever it already builded
            hash_digest = hashlib.sha256(buff.getbuffer()).hexdigest()

            try:
                info = await self.stat_object(bucket_name, object_name)

                # logger.info(f"{info = }")
                # logger.info(f"{info.metadata = }")

                if (
                    not ignore_cache
                    and info.metadata
                    and info.metadata.get("x-amz-meta-dtc-checksum-sha256", None) == hash_digest
                ):
                    return hash_digest
            except S3Error as ex:
                pass

            size = len(buff.getbuffer())
            await self.put_object(
                bucket_name,
                object_name,
                buff,
                length=size,
                metadata={"dtc-checksum-sha256": hash_digest},
            )

            logger.info(
                f"Uploaded archive from {source!r} ({size = }) "
                f"(hash: {hash_digest}) as 's3://{bucket_name}/{object_name}'",
            )

        return hash_digest

    async def intelligent_put_object(
        self,
        data: BinaryIO,
        bucket_name: str,
        object_name: str,
        *,
        hash_block_size: int = 2**16,
        ignore_cache: bool = False,
    ) -> str:
        hash_obj = hashlib.sha256()
        while data.readable():
            block = data.read(hash_block_size)
            if not block:
                break
            hash_obj.update(block)
        size = data.tell()
        data.seek(0)
        hash_digest = hash_obj.hexdigest()

        try:
            info = await self.stat_object(bucket_name, object_name)

            if (
                not ignore_cache
                and info.metadata
                and info.metadata.get("x-amz-meta-dtc-checksum-sha256", None) == hash_digest
            ):
                return hash_digest
        except S3Error as ex:
            pass

        await self.put_object(
            bucket_name,
            object_name,
            data,
            length=size,
            metadata={"dtc-checksum-sha256": hash_digest},
        )

        logger.info(
            f"Uploaded object ({size = }) (hash: {hash_digest}) as 's3://{bucket_name}/{object_name}'",
        )

        return hash_digest

    def __init__(
        self,
        session_token=None,  # noqa: ANN001
        credentials=None,  # noqa: ANN001
        cert_check=True,  # noqa: ANN001, FBT002
    ):
        super().__init__(
            endpoint=settings.s3_endpoint,
            access_key=settings.S3_ACCESS,
            secret_key=settings.S3_SECRET,
            secure=settings.S3_HTTPS,
            region=settings.S3_REGION,
            #
            session_token=session_token,
            credentials=credentials,
            cert_check=cert_check,
        )
        # FIXME: monkeypatch
        self.s3client = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(
                resolver=aiohttp.ThreadedResolver(),
            ),
        )

    async def _url_open(
        self,
        method,
        region,
        bucket_name=None,
        object_name=None,
        body=None,
        headers=None,
        query_params=None,
        session=None,
    ):
        # if session is None:
        session = self.s3client

        return await super()._url_open(
            method,
            region,
            bucket_name,
            object_name,
            body,
            headers,
            query_params,
            session,
        )

    async def _execute(
        self,
        method,
        bucket_name=None,
        object_name=None,
        body=None,
        headers=None,
        query_params=None,
        session=None,
    ):
        session = self.s3client

        return await super()._execute(
            method,
            bucket_name,
            object_name,
            body,
            headers,
            query_params,
            session,
        )
