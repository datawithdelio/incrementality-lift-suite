import tomllib
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from incrementality_api.core.config import Settings
from incrementality_api.workers import main as worker_main


class FakeS3Client:
    pass


class FakeWorker:
    def __init__(self) -> None:
        self.run_count = 0

    async def run_forever(self) -> None:
        self.run_count += 1


class FakeEngine:
    def __init__(self) -> None:
        self.dispose_count = 0

    async def dispose(self) -> None:
        self.dispose_count += 1


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=("postgresql+asyncpg://user:password@localhost:55432/incrementality"),
        dataset_validation_read_chunk_bytes=64_000,
        dataset_validation_spool_max_memory_bytes=128_000,
        dataset_validation_job_max_attempts=4,
        dataset_validation_job_retry_delay_seconds=45,
        dataset_validation_job_claim_timeout_seconds=120,
        dataset_validation_worker_poll_interval_seconds=0.25,
        dataset_validation_worker_error_retry_seconds=2.5,
        s3_endpoint_url="http://localhost:5001",
        s3_access_key="test-access",
        s3_secret_key="test-secret",
        s3_bucket="test-artifacts",
        s3_region="us-east-1",
    )


def test_builds_complete_production_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = build_settings()
    fake_client = FakeS3Client()
    fake_session_factory = object()

    captured_s3_arguments: dict[str, Any] = {}

    def fake_create_s3_client(
        **arguments: Any,
    ) -> FakeS3Client:
        captured_s3_arguments.update(arguments)
        return fake_client

    monkeypatch.setattr(
        worker_main,
        "get_settings",
        lambda: settings,
        raising=False,
    )
    monkeypatch.setattr(
        worker_main,
        "get_session_factory",
        lambda: fake_session_factory,
        raising=False,
    )
    monkeypatch.setattr(
        worker_main,
        "create_s3_compatible_client",
        fake_create_s3_client,
        raising=False,
    )

    worker = worker_main.build_dataset_validation_worker()

    assert worker._poll_interval_seconds == 0.25
    assert worker._error_retry_seconds == 2.5

    process_next = worker._process_next

    assert process_next._recover_stale is not None
    assert process_next._recover_stale._claim_timeout == timedelta(seconds=120)

    assert process_next._record_failure._retry_delay == timedelta(seconds=45)

    validate_dataset = process_next._validate_dataset

    assert validate_dataset._read_chunk_size == 64_000
    assert validate_dataset._content_validator._spool_max_memory_bytes == 128_000

    object_storage = validate_dataset._object_storage

    assert object_storage._client is fake_client
    assert object_storage._bucket_name == ("test-artifacts")
    assert object_storage._spool_max_memory_bytes == 128_000

    assert captured_s3_arguments == {
        "endpoint_url": "http://localhost:5001",
        "access_key": "test-access",
        "secret_key": "test-secret",
        "region": "us-east-1",
    }


@pytest.mark.asyncio
async def test_main_runs_worker_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = FakeWorker()
    engine = FakeEngine()
    logging_calls: list[str] = []

    monkeypatch.setattr(
        worker_main,
        "build_dataset_validation_worker",
        lambda: worker,
    )
    monkeypatch.setattr(
        worker_main,
        "get_engine",
        lambda: engine,
        raising=False,
    )
    monkeypatch.setattr(
        worker_main,
        "configure_logging",
        lambda: logging_calls.append("configured"),
        raising=False,
    )

    await worker_main.main()

    assert logging_calls == ["configured"]
    assert worker.run_count == 1
    assert engine.dispose_count == 1


def test_pyproject_exposes_worker_console_script() -> None:
    configuration = tomllib.loads(Path("pyproject.toml").read_text())

    assert (
        configuration["project"]["scripts"]["incrementality-worker"]
        == "incrementality_api.workers.main:run"
    )
