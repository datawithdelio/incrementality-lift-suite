from datetime import datetime
from types import SimpleNamespace
from typing import cast

from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.api.dependencies import (
    datasets as dataset_dependencies,
)
from incrementality_api.application.datasets.ports import (
    DatasetClock,
    DatasetObjectStorage,
    DatasetUploadUnitOfWork,
)
from incrementality_api.application.datasets.upload_dataset import (
    UploadDataset,
)
from incrementality_api.infrastructure.storage.s3_dataset_objects import (
    S3CompatibleClient,
)


def test_constructs_production_upload_service(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    session_factory = cast(
        async_sessionmaker[AsyncSession],
        object(),
    )
    unit_of_work = cast(
        DatasetUploadUnitOfWork,
        object(),
    )
    s3_client = cast(
        S3CompatibleClient,
        object(),
    )
    object_storage = cast(
        DatasetObjectStorage,
        object(),
    )
    clock = cast(
        DatasetClock,
        object(),
    )
    upload_service = cast(
        UploadDataset,
        object(),
    )

    settings = SimpleNamespace(
        s3_endpoint_url="http://localhost:5001",
        s3_access_key="incrementality",
        s3_secret_key="incrementality-secret",
        s3_bucket="incrementality-artifacts",
        s3_region="us-east-1",
        dataset_upload_spool_max_memory_bytes=8_388_608,
    )

    monkeypatch.setattr(
        dataset_dependencies,
        "get_settings",
        lambda: settings,
    )

    monkeypatch.setattr(
        dataset_dependencies,
        "get_session_factory",
        lambda: session_factory,
    )

    def fake_unit_of_work(
        *,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> DatasetUploadUnitOfWork:
        captured["session_factory"] = session_factory
        return unit_of_work

    monkeypatch.setattr(
        dataset_dependencies,
        "SqlAlchemyDatasetUnitOfWork",
        fake_unit_of_work,
    )

    def fake_create_client(
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str,
    ) -> S3CompatibleClient:
        captured["endpoint_url"] = endpoint_url
        captured["access_key"] = access_key
        captured["secret_key"] = secret_key
        captured["region"] = region
        return s3_client

    monkeypatch.setattr(
        dataset_dependencies,
        "create_s3_compatible_client",
        fake_create_client,
        raising=False,
    )

    def fake_object_storage(
        *,
        client: S3CompatibleClient,
        bucket_name: str,
        spool_max_memory_bytes: int,
    ) -> DatasetObjectStorage:
        captured["client"] = client
        captured["bucket_name"] = bucket_name
        captured["spool_max_memory_bytes"] = spool_max_memory_bytes
        return object_storage

    monkeypatch.setattr(
        dataset_dependencies,
        "S3DatasetObjectStorage",
        fake_object_storage,
        raising=False,
    )

    class FakeSystemClock:
        def __new__(cls) -> DatasetClock:
            return clock

    monkeypatch.setattr(
        dataset_dependencies,
        "SystemDatasetClock",
        FakeSystemClock,
        raising=False,
    )

    def fake_upload_dataset(
        *,
        unit_of_work: DatasetUploadUnitOfWork,
        object_storage: DatasetObjectStorage,
        clock: DatasetClock,
    ) -> UploadDataset:
        captured["unit_of_work"] = unit_of_work
        captured["object_storage"] = object_storage
        captured["clock"] = clock
        return upload_service

    monkeypatch.setattr(
        dataset_dependencies,
        "UploadDataset",
        fake_upload_dataset,
    )

    result = dataset_dependencies.get_upload_dataset_service()

    assert result is upload_service

    assert captured["session_factory"] is session_factory
    assert captured["unit_of_work"] is unit_of_work

    assert captured["endpoint_url"] == ("http://localhost:5001")
    assert captured["access_key"] == "incrementality"
    assert captured["secret_key"] == ("incrementality-secret")
    assert captured["region"] == "us-east-1"

    assert captured["client"] is s3_client
    assert captured["bucket_name"] == ("incrementality-artifacts")
    assert captured["spool_max_memory_bytes"] == (8_388_608)

    assert captured["object_storage"] is object_storage
    assert captured["clock"] is clock


def test_system_dataset_clock_returns_aware_utc_time() -> None:
    clock = dataset_dependencies.SystemDatasetClock()

    current_time = clock.now()

    assert isinstance(current_time, datetime)
    assert current_time.tzinfo is not None
    assert current_time.utcoffset() is not None
    assert current_time.utcoffset().total_seconds() == 0
