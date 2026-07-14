from io import BytesIO
from typing import BinaryIO

import pytest

from incrementality_api.infrastructure.storage.s3_dataset_objects import (
    S3DatasetObjectStorage,
)

CONTENT = b"market,revenue\nnorth,250\nsouth,175\n"


class FakeStreamingBody:
    def __init__(
        self,
        content: bytes,
        *,
        fail_after_reads: int | None = None,
    ) -> None:
        self._content = BytesIO(content)
        self._fail_after_reads = fail_after_reads
        self.read_sizes: list[int | None] = []
        self.closed = False

    def read(
        self,
        amount: int | None = None,
    ) -> bytes:
        if self._fail_after_reads is not None and len(self.read_sizes) >= self._fail_after_reads:
            raise RuntimeError("S3 response stream failed.")

        self.read_sizes.append(amount)

        if amount is None:
            return self._content.read()

        return self._content.read(amount)

    def close(self) -> None:
        self.closed = True
        self._content.close()


class FakeS3Client:
    def __init__(
        self,
        *,
        content: bytes = CONTENT,
        fail_after_reads: int | None = None,
    ) -> None:
        self.streaming_body = FakeStreamingBody(
            content,
            fail_after_reads=fail_after_reads,
        )
        self.get_calls: list[tuple[str, str]] = []

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> object:
        self.get_calls.append(
            (
                Bucket,
                Key,
            )
        )

        return {
            "Body": self.streaming_body,
        }

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: BinaryIO,
        ContentType: str,
    ) -> object:
        del Bucket, Key, Body, ContentType
        raise AssertionError("put_object must not be called while reading.")

    def delete_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> object:
        del Bucket, Key
        raise AssertionError("delete_object must not be called while reading.")


@pytest.mark.asyncio
async def test_reads_object_in_bounded_chunks() -> None:
    client = FakeS3Client()

    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    chunks = [
        chunk
        async for chunk in storage.read(
            storage_key="datasets/results.csv",
            chunk_size=7,
        )
    ]

    assert b"".join(chunks) == CONTENT
    assert chunks
    assert all(0 < len(chunk) <= 7 for chunk in chunks)

    assert client.get_calls == [
        (
            "incrementality-artifacts",
            "datasets/results.csv",
        )
    ]

    assert client.streaming_body.read_sizes
    assert all(size == 7 for size in client.streaming_body.read_sizes)
    assert client.streaming_body.closed is True


@pytest.mark.asyncio
async def test_rejects_nonpositive_read_chunk_size() -> None:
    client = FakeS3Client()

    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    with pytest.raises(
        ValueError,
        match="Read chunk size must be positive",
    ):
        async for _ in storage.read(
            storage_key="datasets/results.csv",
            chunk_size=0,
        ):
            pass

    assert client.get_calls == []


@pytest.mark.asyncio
async def test_closes_response_when_consumer_stops_early() -> None:
    client = FakeS3Client()

    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    stream = storage.read(
        storage_key="datasets/results.csv",
        chunk_size=5,
    )

    first_chunk = await anext(stream)

    assert first_chunk == CONTENT[:5]
    assert client.streaming_body.closed is False

    await stream.aclose()

    assert client.streaming_body.closed is True


@pytest.mark.asyncio
async def test_closes_response_when_stream_read_fails() -> None:
    client = FakeS3Client(
        fail_after_reads=1,
    )

    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name="incrementality-artifacts",
    )

    with pytest.raises(
        RuntimeError,
        match="S3 response stream failed",
    ):
        async for _ in storage.read(
            storage_key="datasets/results.csv",
            chunk_size=5,
        ):
            pass

    assert client.streaming_body.closed is True
