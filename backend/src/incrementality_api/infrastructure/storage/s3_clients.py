from typing import cast

import boto3
from botocore.config import Config

from incrementality_api.infrastructure.storage.s3_dataset_objects import (
    S3CompatibleClient,
)


def create_s3_compatible_client(
    *,
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    region: str,
) -> S3CompatibleClient:
    """Create the blocking S3 client used by object storage."""

    configuration = Config(
        signature_version="s3v4",
        retries={
            "mode": "standard",
            "total_max_attempts": 4,
        },
        s3={
            "addressing_style": "path",
        },
    )

    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=configuration,
    )

    return cast(
        S3CompatibleClient,
        client,
    )
