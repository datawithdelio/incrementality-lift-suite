import tomllib
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from incrementality_api.application.data_products.reconciliation import (
    CompositeReportArtifactReconciliationRecorder,
)
from incrementality_api.core.config import Settings
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.infrastructure.database.repositories.report_reconciliation import (
    SqlAlchemyReportArtifactReconciliationRecorder,
)
from incrementality_api.infrastructure.estimation.geo_holdout import (
    StatsmodelsGeoHoldoutEstimator,
)
from incrementality_api.infrastructure.estimation.marketing_mix_model import (
    BayesianMarketingMixEstimator,
)
from incrementality_api.infrastructure.estimation.runtime_versions import (
    StatisticalRuntimeVersionProvider,
)
from incrementality_api.infrastructure.estimation.synthetic_control import (
    ScipySyntheticControlEstimator,
)
from incrementality_api.infrastructure.observability.report_reconciliation import (
    LoggingReportArtifactReconciliationRecorder,
)
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
        analysis_execution_retry_delay_seconds=45,
        analysis_execution_worker_poll_interval_seconds=0.5,
        analysis_execution_worker_error_retry_seconds=3.0,
        report_artifact_reconciliation_interval_seconds=900,
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


def test_builds_complete_analysis_execution_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = build_settings()
    fake_client = FakeS3Client()
    fake_session_factory = object()
    monkeypatch.setattr(worker_main, "get_settings", lambda: settings)
    monkeypatch.setattr(
        worker_main,
        "get_session_factory",
        lambda: fake_session_factory,
    )
    monkeypatch.setattr(
        worker_main,
        "create_s3_compatible_client",
        lambda **_arguments: fake_client,
    )

    worker = worker_main.build_analysis_execution_worker()

    assert worker._poll_interval_seconds == 0.5
    assert worker._error_retry_seconds == 3.0
    process_next = worker._process_next
    assert process_next._claim_next is not None
    assert process_next._input_loader is not None
    assert process_next._estimator_selector is not None
    assert isinstance(
        process_next._statistical_runtime_versions,
        StatisticalRuntimeVersionProvider,
    )
    assert set(process_next._input_loader._additional_builders) == {
        AnalysisEstimatorType.SYNTHETIC_CONTROL,
        AnalysisEstimatorType.GEO_HOLDOUT,
        AnalysisEstimatorType.MARKETING_MIX_MODEL,
        AnalysisEstimatorType.OFF_POLICY_EVALUATION,
    }
    assert isinstance(
        process_next._estimator_selector.select(AnalysisEstimatorType.SYNTHETIC_CONTROL),
        ScipySyntheticControlEstimator,
    )
    assert isinstance(
        process_next._estimator_selector.select(AnalysisEstimatorType.GEO_HOLDOUT),
        StatsmodelsGeoHoldoutEstimator,
    )
    assert isinstance(
        process_next._estimator_selector.select(AnalysisEstimatorType.MARKETING_MIX_MODEL),
        BayesianMarketingMixEstimator,
    )
    assert process_next._persist_success is not None
    assert process_next._record_retryable_failure._retry_policy._retry_delay == timedelta(
        seconds=45
    )
    assert process_next._mark_failed is not None


@pytest.mark.asyncio
async def test_main_runs_worker_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validation_worker = FakeWorker()
    analysis_worker = FakeWorker()
    report_worker = FakeWorker()
    engine = FakeEngine()
    logging_calls: list[str] = []

    monkeypatch.setattr(
        worker_main,
        "build_dataset_validation_worker",
        lambda: validation_worker,
    )
    monkeypatch.setattr(
        worker_main,
        "build_analysis_execution_worker",
        lambda: analysis_worker,
    )
    monkeypatch.setattr(
        worker_main,
        "build_report_generation_worker",
        lambda: report_worker,
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
    assert validation_worker.run_count == 1
    assert analysis_worker.run_count == 1
    assert report_worker.run_count == 1
    assert engine.dispose_count == 1


def test_pyproject_exposes_worker_console_script() -> None:
    configuration = tomllib.loads(Path("pyproject.toml").read_text())

    assert (
        configuration["project"]["scripts"]["incrementality-worker"]
        == "incrementality_api.workers.main:run"
    )


def test_builds_report_worker_with_stale_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        report_generation_job_claim_timeout_seconds=180,
    )
    fake_client = FakeS3Client()
    fake_session_factory = object()

    monkeypatch.setattr(
        worker_main,
        "get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        worker_main,
        "get_session_factory",
        lambda: fake_session_factory,
    )
    monkeypatch.setattr(
        worker_main,
        "create_s3_compatible_client",
        lambda **_arguments: fake_client,
    )

    worker = worker_main.build_report_generation_worker()
    process_next = worker._process_next

    assert process_next._recover_stale is not None
    assert process_next._recover_stale._claim_timeout == timedelta(seconds=180)


def test_builds_report_artifact_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = build_settings()
    fake_client = FakeS3Client()
    fake_session_factory = object()

    monkeypatch.setattr(
        worker_main,
        "get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        worker_main,
        "get_session_factory",
        lambda: fake_session_factory,
    )
    monkeypatch.setattr(
        worker_main,
        "create_s3_compatible_client",
        lambda **_arguments: fake_client,
    )

    worker = worker_main.build_report_generation_worker()
    process_next = worker._process_next

    assert process_next._reconcile_artifacts is not None

    periodic = process_next._reconcile_artifacts

    assert periodic._interval == timedelta(seconds=900)
    assert periodic._clock is process_next._clock
    assert periodic._reconciliation._repository is process_next._repository
    assert periodic._reconciliation._storage is process_next._storage
    recorder = periodic._reconciliation._recorder

    assert isinstance(
        recorder,
        CompositeReportArtifactReconciliationRecorder,
    )
    assert len(recorder._recorders) == 2
    assert isinstance(
        recorder._recorders[0],
        SqlAlchemyReportArtifactReconciliationRecorder,
    )
    assert recorder._recorders[0]._sessions is fake_session_factory
    assert isinstance(
        recorder._recorders[1],
        LoggingReportArtifactReconciliationRecorder,
    )
    assert process_next._storage._client is fake_client
