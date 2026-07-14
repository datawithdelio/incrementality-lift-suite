from typing import cast

from botocore.config import Config
from pytest import MonkeyPatch

from incrementality_api.infrastructure.storage import (
    s3_clients,
)


def test_creates_path_style_s3v4_client(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    sentinel_client = object()

    def fake_boto3_client(
        service_name: str,
        **kwargs: object,
    ) -> object:
        captured["service_name"] = service_name
        captured.update(kwargs)

        return sentinel_client

    monkeypatch.setattr(
        s3_clients.boto3,
        "client",
        fake_boto3_client,
    )

    result = s3_clients.create_s3_compatible_client(
        endpoint_url="http://localhost:5000",
        access_key="incrementality",
        secret_key="incrementality-secret",
        region="us-east-1",
    )

    assert result is sentinel_client

    assert captured["service_name"] == "s3"
    assert captured["endpoint_url"] == ("http://localhost:5000")
    assert captured["aws_access_key_id"] == ("incrementality")
    assert captured["aws_secret_access_key"] == ("incrementality-secret")
    assert captured["region_name"] == "us-east-1"

    configuration = cast(
        Config,
        captured["config"],
    )

    assert configuration.signature_version == "s3v4"
    assert configuration.s3 is not None
    assert configuration.s3["addressing_style"] == "path"

    assert configuration.retries is not None
    assert configuration.retries["mode"] == "standard"
    assert configuration.retries["total_max_attempts"] == 4
