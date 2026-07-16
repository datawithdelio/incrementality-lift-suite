import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.analysis_results.get_analysis_result import (
    AnalysisResultUnavailableError,
    GetAnalysisResult,
    GetAnalysisResultQuery,
)
from incrementality_api.domain.analysis_results.entities import AnalysisResult
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

NOW = datetime(2026, 7, 14, 20, 0, tzinfo=UTC)


class FakeRepository:
    def __init__(self, value: object | None) -> None:
        self.value = value

    async def get_by_scope(self, **scope: UUID) -> object | None:
        del scope
        return self.value

    async def get_by_analysis_run_scope(self, **scope: UUID) -> object | None:
        del scope
        return self.value


class FakeUnitOfWork:
    def __init__(
        self,
        run: AnalysisRun | None,
        job: AnalysisExecutionJob | None,
        result: AnalysisResult | None,
    ) -> None:
        self.analysis_runs = FakeRepository(run)
        self.execution_jobs = FakeRepository(job)
        self.analysis_results = FakeRepository(result)

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, *args: object) -> None:
        del args


def build_run() -> AnalysisRun:
    return AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256="c" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=1,
        created_by_user_id=uuid4(),
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        estimator_version="did-v2",
        random_seed=1_729,
        configuration_json='{"intervention_time":"2026-01-01T00:00:00+00:00"}',
        created_at=NOW,
    )


@pytest.mark.asyncio
async def test_returns_pending_run_without_result() -> None:
    run = build_run()
    job = AnalysisExecutionJob.enqueue(
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        analysis_run_id=run.id,
        created_at=NOW,
        available_at=NOW,
    )
    service = GetAnalysisResult(unit_of_work=FakeUnitOfWork(run, job, None))

    view = await service.execute(GetAnalysisResultQuery(run.workspace_id, run.project_id, run.id))

    assert view.lifecycle_status == "queued"
    assert view.result is None
    assert view.configuration == json.loads(run.configuration_json)


@pytest.mark.asyncio
async def test_returns_retrying_when_running_run_has_pending_attempted_job() -> None:
    run = build_run().start(started_at=NOW)
    job = (
        AnalysisExecutionJob.enqueue(
            workspace_id=run.workspace_id,
            project_id=run.project_id,
            analysis_run_id=run.id,
            created_at=NOW,
            available_at=NOW,
        )
        .claim(claimed_at=NOW)
        .retry(
            failed_at=NOW,
            available_at=NOW,
            error="temporary service outage",
        )
    )

    view = await GetAnalysisResult(unit_of_work=FakeUnitOfWork(run, job, None)).execute(
        GetAnalysisResultQuery(run.workspace_id, run.project_id, run.id)
    )

    assert view.lifecycle_status == "retrying"
    assert view.failure_information == (
        "A temporary issue interrupted analysis. It will retry automatically."
    )
    assert view.attempt_count == 1


@pytest.mark.asyncio
async def test_missing_or_cross_tenant_run_is_not_found() -> None:
    query = GetAnalysisResultQuery(uuid4(), uuid4(), uuid4())
    with pytest.raises(AnalysisResultUnavailableError):
        await GetAnalysisResult(unit_of_work=FakeUnitOfWork(None, None, None)).execute(query)
