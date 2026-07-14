from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID, uuid4

import pytest
from incrementality_api.application.analysis_execution.claim_next_execution_job import (
    ClaimNextAnalysisExecutionJob,
)
from incrementality_api.application.analysis_execution.errors import (
    AnalysisExecutionRunUnavailableError,
)

from incrementality_api.domain.analysis_runs.entities import (
    AnalysisRun,
)
from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)

CREATED_AT = datetime(
    2026,
    7,
    17,
    10,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    17,
    10,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    17,
    10,
    2,
    tzinfo=UTC,
)


class FixedClock:
    def __init__(self) -> None:
        self.call_count = 0

    def now(self) -> datetime:
        self.call_count += 1
        return CLAIMED_AT


def build_queued_run(
    *,
    workspace_id: UUID,
    project_id: UUID,
) -> AnalysisRun:
    return AnalysisRun.queue(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=uuid4(),
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=1,
        created_by_user_id=uuid4(),
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        configuration_json='{"alpha":0.05}',
        created_at=CREATED_AT,
    )


def build_pending_job(
    *,
    run: AnalysisRun,
) -> AnalysisExecutionJob:
    return AnalysisExecutionJob.enqueue(
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        analysis_run_id=run.id,
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=3,
    )


class FakeExecutionJobRepository:
    def __init__(
        self,
        job: AnalysisExecutionJob | None,
    ) -> None:
        self._job = job
        self.received_available_at: datetime | None = None
        self.updated: list[AnalysisExecutionJob] = []

    async def get_next_available_for_update(
        self,
        *,
        available_at: datetime,
    ) -> AnalysisExecutionJob | None:
        self.received_available_at = available_at
        return self._job

    async def update(
        self,
        job: AnalysisExecutionJob,
    ) -> None:
        self.updated.append(job)


class FakeAnalysisRunRepository:
    def __init__(
        self,
        run: AnalysisRun | None,
    ) -> None:
        self._run = run
        self.received_scope: tuple[UUID, UUID, UUID] | None = None
        self.updated: list[AnalysisRun] = []

    async def get_by_scope_for_update(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisRun | None:
        self.received_scope = (
            workspace_id,
            project_id,
            analysis_run_id,
        )
        return self._run

    async def update(
        self,
        run: AnalysisRun,
    ) -> None:
        self.updated.append(run)


class FakeAnalysisExecutionUnitOfWork:
    def __init__(
        self,
        *,
        job: AnalysisExecutionJob | None,
        run: AnalysisRun | None,
    ) -> None:
        self.execution_jobs = FakeExecutionJobRepository(job)
        self.analysis_runs = FakeAnalysisRunRepository(run)
        self.enter_count = 0
        self.commit_count = 0
        self.exit_exception_type: type[BaseException] | None = None

    async def __aenter__(
        self,
    ) -> "FakeAnalysisExecutionUnitOfWork":
        self.enter_count += 1
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception
        del traceback

        self.exit_exception_type = exception_type

    async def commit(self) -> None:
        self.commit_count += 1


@pytest.mark.asyncio
async def test_returns_none_when_no_job_is_available() -> None:
    unit_of_work = FakeAnalysisExecutionUnitOfWork(
        job=None,
        run=None,
    )
    clock = FixedClock()

    result = await ClaimNextAnalysisExecutionJob(
        unit_of_work=unit_of_work,
        clock=clock,
    ).execute()

    assert result is None
    assert clock.call_count == 1
    assert unit_of_work.execution_jobs.received_available_at == CLAIMED_AT
    assert unit_of_work.analysis_runs.received_scope is None
    assert unit_of_work.execution_jobs.updated == []
    assert unit_of_work.analysis_runs.updated == []
    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
async def test_claims_job_and_starts_analysis_run_atomically() -> None:
    workspace_id = uuid4()
    project_id = uuid4()

    queued_run = build_queued_run(
        workspace_id=workspace_id,
        project_id=project_id,
    )
    pending_job = build_pending_job(
        run=queued_run,
    )

    unit_of_work = FakeAnalysisExecutionUnitOfWork(
        job=pending_job,
        run=queued_run,
    )
    clock = FixedClock()

    result = await ClaimNextAnalysisExecutionJob(
        unit_of_work=unit_of_work,
        clock=clock,
    ).execute()

    assert result is not None
    assert result.status is (AnalysisExecutionJobStatus.RUNNING)
    assert result.attempt_count == 1
    assert result.claimed_at == CLAIMED_AT

    assert unit_of_work.execution_jobs.updated == [result]

    assert unit_of_work.analysis_runs.received_scope == (
        workspace_id,
        project_id,
        queued_run.id,
    )

    assert len(unit_of_work.analysis_runs.updated) == 1

    running_run = unit_of_work.analysis_runs.updated[0]

    assert running_run.status is (AnalysisRunStatus.RUNNING)
    assert running_run.started_at == CLAIMED_AT
    assert running_run.id == queued_run.id

    assert clock.call_count == 1
    assert unit_of_work.commit_count == 1
    assert unit_of_work.exit_exception_type is None


@pytest.mark.asyncio
async def test_missing_analysis_run_prevents_claim_commit() -> None:
    queued_run = build_queued_run(
        workspace_id=uuid4(),
        project_id=uuid4(),
    )
    pending_job = build_pending_job(
        run=queued_run,
    )

    unit_of_work = FakeAnalysisExecutionUnitOfWork(
        job=pending_job,
        run=None,
    )

    with pytest.raises(
        AnalysisExecutionRunUnavailableError,
        match="Analysis run is unavailable",
    ):
        await ClaimNextAnalysisExecutionJob(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute()

    assert unit_of_work.execution_jobs.updated == []
    assert unit_of_work.analysis_runs.updated == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.exit_exception_type is AnalysisExecutionRunUnavailableError
