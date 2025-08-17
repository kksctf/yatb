import hashlib
import io
import tarfile
from gzip import GzipFile
from pathlib import Path
from typing import IO, cast

import aiohttp
from loguru import logger
from miniopy_async import Minio, S3Error


class MinioEx(Minio):
    s3client: aiohttp.ClientSession

    async def setup_buckets(self, buckets: list[str]) -> None:
        for bucket in buckets:
            if not await self.bucket_exists(bucket):
                await self.make_bucket(bucket)
                logger.info(f"Created s3 {bucket = }")

    async def upload_directory(self, source: Path, bucket_name: str, object_name: str) -> str:
        assert source.is_absolute()
        assert source.is_dir()

        with io.BytesIO() as buff:
            with (
                # have to separately create gzip, because we need to setup mtime=0
                GzipFile(fileobj=buff, mode="wb", mtime=0) as gzip,
                tarfile.open(
                    # https://stackoverflow.com/a/58407810
                    fileobj=cast(IO[bytes], gzip),  # IDK WHY, but for some reason gzip is not IO[bytes]...
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

                if info.metadata and info.metadata["x-amz-meta-dtc-checksum-sha256"] == hash_digest:
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

    def __init__(
        self,
        endpoint,
        access_key=None,
        secret_key=None,
        session_token=None,
        secure=True,
        region=None,
        credentials=None,
        cert_check=True,
    ):
        super().__init__(
            endpoint,
            access_key,
            secret_key,
            session_token,
            secure,
            region,
            credentials,
            cert_check,
        )
        # FIXME: monkeypatch
        self.s3client = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(
                resolver=aiohttp.ThreadedResolver(),
                # resolver=aiohttp.AsyncResolver(
                #     nameservers=[
                #         "203:e236:d155:b11c:ce6d:8c03:6e72:9a41",
                #     ],
                # ),
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

        return await super()._url_open(method, region, bucket_name, object_name, body, headers, query_params, session)

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
