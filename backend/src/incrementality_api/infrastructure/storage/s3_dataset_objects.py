import asyncio
from collections.abc import AsyncIterator, Mapping
from hashlib import sha256
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Protocol, cast

from botocore.exceptions import ClientError

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

    def list_objects_v2(
        self,
        *,
        Bucket: str,
        Prefix: str,
        ContinuationToken: str | None = None,
    ) -> Mapping[str, object]:
        """List objects beneath a prefix."""

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Retrieve object metadata without downloading its content."""

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

    async def list_keys(
        self,
        *,
        prefix: str,
    ) -> tuple[str, ...]:
        keys: list[str] = []
        continuation_token: str | None = None

        while True:
            if continuation_token is None:
                response = await asyncio.to_thread(
                    self._client.list_objects_v2,
                    Bucket=self._bucket_name,
                    Prefix=prefix,
                )
            else:
                response = await asyncio.to_thread(
                    self._client.list_objects_v2,
                    Bucket=self._bucket_name,
                    Prefix=prefix,
                    ContinuationToken=continuation_token,
                )

            contents = response.get("Contents", ())

            if isinstance(contents, list):
                for item in contents:
                    if not isinstance(item, Mapping):
                        continue

                    key = item.get("Key")

                    if isinstance(key, str):
                        keys.append(key)

            if response.get("IsTruncated") is not True:
                break

            next_token = response.get(
                "NextContinuationToken"
            )

            if not isinstance(next_token, str) or not next_token:
                raise RuntimeError(
                    "S3 listing was truncated without a continuation token."
                )

            continuation_token = next_token

        return tuple(keys)

    async def exists(
        self,
        *,
        storage_key: str,
    ) -> bool:
        try:
            await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._bucket_name,
                Key=storage_key,
            )
        except ClientError as error:
            error_details = error.response.get("Error", {})
            response_metadata = error.response.get("ResponseMetadata", {})

            error_code = str(error_details.get("Code", ""))
            http_status = response_metadata.get("HTTPStatusCode")

            if http_status == 404 or error_code in {
                "404",
                "NoSuchKey",
                "NotFound",
            }:
                return False

            raise

        return True

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

    def read_chunks(
        self,
        storage_key: str,
    ) -> AsyncIterator[bytes]:
        """Adapt dataset reads to the analysis-input object-reader port."""
        return self.read(storage_key=storage_key)

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
