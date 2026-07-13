import asyncio
import os
from collections.abc import AsyncIterator
from hashlib import sha256
from typing import cast
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from mypy_boto3_s3 import S3Client

from incrementality_api.infrastructure.storage.s3_clients import (
    create_s3_compatible_client,
)
from incrementality_api.infrastructure.storage.s3_dataset_objects import (
    S3DatasetObjectStorage,
)

RUN_S3_INTEGRATION = os.getenv("RUN_S3_INTEGRATION") == "1"

S3_ENDPOINT_URL = os.getenv(
    "S3_INTEGRATION_ENDPOINT_URL",
    "http://localhost:5001",
)

CONTENT = b"market,revenue\nnorth,250\n"
CONTENT_CHECKSUM = sha256(CONTENT).hexdigest()


async def content_chunks() -> AsyncIterator[bytes]:
    yield CONTENT[:7]
    yield CONTENT[7:17]
    yield CONTENT[17:]


@pytest.mark.skipif(
    not RUN_S3_INTEGRATION,
    reason="S3 integration tests are disabled.",
)
@pytest.mark.asyncio
async def test_writes_reads_and_deletes_real_s3_object() -> None:
    client = cast(
        S3Client,
        create_s3_compatible_client(
            endpoint_url=S3_ENDPOINT_URL,
            access_key="incrementality",
            secret_key="incrementality-secret",
            region="us-east-1",
        ),
    )

    bucket_name = f"incrementality-test-{uuid4().hex}"
    storage_key = (
        "workspaces/test-workspace/"
        "projects/test-project/"
        f"datasets/{CONTENT_CHECKSUM}/"
        "campaign-results.csv"
    )

    await asyncio.to_thread(
        client.create_bucket,
        Bucket=bucket_name,
    )

    storage = S3DatasetObjectStorage(
        client=client,
        bucket_name=bucket_name,
        spool_max_memory_bytes=8,
    )

    try:
        result = await storage.write(
            storage_key=storage_key,
            media_type="text/csv",
            chunks=content_chunks(),
        )

        assert result.byte_size == len(CONTENT)
        assert result.checksum_sha256 == (CONTENT_CHECKSUM)

        response = await asyncio.to_thread(
            client.get_object,
            Bucket=bucket_name,
            Key=storage_key,
        )

        stored_content = await asyncio.to_thread(
            response["Body"].read,
        )

        assert stored_content == CONTENT
        assert response["ContentType"] == "text/csv"

        await storage.delete(
            storage_key=storage_key,
        )

        with pytest.raises(ClientError) as error:
            await asyncio.to_thread(
                client.get_object,
                Bucket=bucket_name,
                Key=storage_key,
            )

        assert error.value.response["Error"]["Code"] in {
            "NoSuchKey",
            "404",
        }
    finally:
        await asyncio.to_thread(
            client.delete_object,
            Bucket=bucket_name,
            Key=storage_key,
        )

        await asyncio.to_thread(
            client.delete_bucket,
            Bucket=bucket_name,
        )
