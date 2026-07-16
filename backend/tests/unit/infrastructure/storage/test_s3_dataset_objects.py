from collections.abc import AsyncIterator
from hashlib import sha256
from typing import BinaryIO

import pytest
from botocore.exceptions import ClientError

from incrementality_api.infrastructure.storage.s3_dataset_objects import (
    S3DatasetObjectStorage,
)

CONTENT = b"market,revenue\nnorth,250\n"
CONTENT_CHECKSUM = sha256(CONTENT).hexdigest()


async def content_chunks() -> AsyncIterator[bytes]:
    yield CONTENT[:5]
    yield b""
    yield CONTENT[5:17]
    yield CONTENT[17:]


async def failing_chunks() -> AsyncIterator[bytes]:
    yield CONTENT[:5]

    raise RuntimeError("Incoming stream failed.")


class FakeS3Client:
    def __init__(self) -> None:
        self.put_calls: list[tuple[str, str, str, bytes]] = []
        self.delete_calls: list[tuple[str, str]] = []
        self.body_was_rolled_to_disk = False

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: BinaryIO,
        ContentType: str,
    ) -> object:
        self.body_was_rolled_to_disk = bool(
            getattr(
                Body,
                "_rolled",
                False,
            )
        )

        self.put_calls.append(
            (
                Bucket,
                Key,
                ContentType,
                Body.read(),
            )
        )

        return {
            "ETag": "fake-etag",
        }

    def delete_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> object:
        self.delete_calls.append(
            (
                Bucket,
                Key,
            )
        )

        return {}


@pytest.mark.asyncio
async def test_streams_object_and_returns_computed_metadata() -> None:
    client = FakeS3Client()

    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    result = await storage.write(
        storage_key=("workspaces/ws/projects/project/datasets/checksum/results.csv"),
        media_type="text/csv",
        chunks=content_chunks(),
    )

    assert result.byte_size == len(CONTENT)
    assert result.checksum_sha256 == CONTENT_CHECKSUM

    assert client.put_calls == [
        (
            "incrementality-artifacts",
            ("workspaces/ws/projects/project/datasets/checksum/results.csv"),
            "text/csv",
            CONTENT,
        )
    ]


@pytest.mark.asyncio
async def test_large_stream_rolls_from_memory_to_disk() -> None:
    client = FakeS3Client()

    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
        spool_max_memory_bytes=4,
    )

    result = await storage.write(
        storage_key="datasets/results.csv",
        media_type="text/csv",
        chunks=content_chunks(),
    )

    assert result.byte_size == len(CONTENT)
    assert client.body_was_rolled_to_disk is True


@pytest.mark.asyncio
async def test_input_stream_failure_does_not_call_s3() -> None:
    client = FakeS3Client()

    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    with pytest.raises(
        RuntimeError,
        match="Incoming stream failed",
    ):
        await storage.write(
            storage_key="datasets/results.csv",
            media_type="text/csv",
            chunks=failing_chunks(),
        )

    assert client.put_calls == []


@pytest.mark.asyncio
async def test_deletes_object_from_configured_bucket() -> None:
    client = FakeS3Client()

    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    await storage.delete(
        storage_key="datasets/results.csv",
    )

    assert client.delete_calls == [
        (
            "incrementality-artifacts",
            "datasets/results.csv",
        )
    ]



class FakeHeadS3Client:
    def __init__(
        self,
        *,
        error_code: str | None = None,
        http_status: int | None = None,
    ) -> None:
        self._error_code = error_code
        self._http_status = http_status
        self.head_calls: list[tuple[str, str]] = []

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> object:
        self.head_calls.append((Bucket, Key))

        if self._error_code is not None:
            raise ClientError(
                {
                    "Error": {
                        "Code": self._error_code,
                        "Message": "Head object failed.",
                    },
                    "ResponseMetadata": {
                        "HTTPStatusCode": self._http_status or 500,
                    },
                },
                "HeadObject",
            )

        return {
            "ContentLength": len(CONTENT),
        }


@pytest.mark.asyncio
async def test_reports_existing_object() -> None:
    client = FakeHeadS3Client()
    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    exists = await storage.exists(
        storage_key="reports/result.pdf",
    )

    assert exists is True
    assert client.head_calls == [
        (
            "incrementality-artifacts",
            "reports/result.pdf",
        )
    ]


@pytest.mark.asyncio
async def test_reports_missing_object_for_not_found_response() -> None:
    client = FakeHeadS3Client(
        error_code="404",
        http_status=404,
    )
    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    exists = await storage.exists(
        storage_key="reports/missing.pdf",
    )

    assert exists is False


@pytest.mark.asyncio
async def test_does_not_hide_permission_or_storage_failures() -> None:
    client = FakeHeadS3Client(
        error_code="AccessDenied",
        http_status=403,
    )
    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    with pytest.raises(ClientError):
        await storage.exists(
            storage_key="reports/restricted.pdf",
        )
