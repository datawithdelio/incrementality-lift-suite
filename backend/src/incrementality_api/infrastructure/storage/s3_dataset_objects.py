import asyncio
from collections.abc import AsyncIterator, Mapping
from hashlib import sha256
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Protocol, cast

from incrementality_api.application.datasets.ports import (
    DatasetObjectWriteResult,
)


class S3StreamingBody(Protocol):
    """Blocking response body returned by an S3 client."""

    def read(
        self,
        amount: int | None = None,
    ) -> bytes:
        """Read up to the requested number of bytes."""

    def close(self) -> None:
        """Close the underlying network response."""


class S3CompatibleClient(Protocol):
    """Minimal blocking S3-client interface used by the adapter."""

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: BinaryIO,
        ContentType: str,
    ) -> object:
        """Store an object."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Retrieve an object and its streaming response body."""

    def delete_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> object:
        """Delete an object."""


class S3DatasetObjectStorage:
    """Stream dataset objects to and from S3-compatible storage."""

    def __init__(
        self,
        *,
        client: S3CompatibleClient,
        bucket_name: str,
        spool_max_memory_bytes: int = 8 * 1024 * 1024,
    ) -> None:
        if not bucket_name.strip():
            raise ValueError("S3 bucket name must not be blank.")

        if spool_max_memory_bytes <= 0:
            raise ValueError("Spool memory limit must be positive.")

        self._client = client
        self._bucket_name = bucket_name
        self._spool_max_memory_bytes = spool_max_memory_bytes

    async def write(
        self,
        *,
        storage_key: str,
        media_type: str,
        chunks: AsyncIterator[bytes],
    ) -> DatasetObjectWriteResult:
        checksum = sha256()
        byte_size = 0

        with SpooledTemporaryFile(
            max_size=self._spool_max_memory_bytes,
            mode="w+b",
        ) as body:
            async for chunk in chunks:
                if not chunk:
                    continue

                body.write(chunk)
                checksum.update(chunk)
                byte_size += len(chunk)

            body.seek(0)

            await asyncio.to_thread(
                self._client.put_object,
                Bucket=self._bucket_name,
                Key=storage_key,
                Body=cast(BinaryIO, body),
                ContentType=media_type,
            )

        return DatasetObjectWriteResult(
            byte_size=byte_size,
            checksum_sha256=checksum.hexdigest(),
        )

    async def read(
        self,
        *,
        storage_key: str,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        if chunk_size <= 0:
            raise ValueError("Read chunk size must be positive.")

        response = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self._bucket_name,
            Key=storage_key,
        )

        body = cast(
            S3StreamingBody,
            response["Body"],
        )

        try:
            while True:
                chunk = await asyncio.to_thread(
                    body.read,
                    chunk_size,
                )

                if not chunk:
                    break

                yield chunk
        finally:
            await asyncio.to_thread(
                body.close,
            )

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket_name,
            Key=storage_key,
        )
