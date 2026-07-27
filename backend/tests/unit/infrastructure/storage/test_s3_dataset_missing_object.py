from collections.abc import AsyncIterator
from typing import Any, cast

import pytest
from botocore.exceptions import ClientError

from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
)
from incrementality_api.infrastructure.storage.s3_dataset_objects import (
    S3DatasetObjectStorage,
)


class MissingObjectClient:
    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> object:
        del Bucket, Key

        raise ClientError(
            {
                "Error": {
                    "Code": "NoSuchKey",
                    "Message": "The specified key does not exist.",
                },
                "ResponseMetadata": {
                    "RequestId": "request-id",
                    "HostId": "host-id",
                    "HTTPStatusCode": 404,
                    "HTTPHeaders": {},
                    "RetryAttempts": 0,
                },
            },
            "GetObject",
        )


@pytest.mark.asyncio
async def test_read_translates_missing_s3_object_to_dataset_unavailable() -> None:
    storage = S3DatasetObjectStorage(
        client=cast(
            Any,
            MissingObjectClient(),
        ),
        bucket_name="datasets",
    )

    stream: AsyncIterator[bytes] = storage.read(
        storage_key="missing.csv",
    )

    with pytest.raises(
        DatasetUnavailableError,
        match="uploaded dataset file is unavailable",
    ):
        await anext(stream)
