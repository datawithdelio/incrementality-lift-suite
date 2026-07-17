from datetime import UTC, datetime, timedelta
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.analysis_execution.errors import (
    AnalysisExecutionJobUnavailableError,
    AnalysisExecutionRunUnavailableError,
)
from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
)
from incrementality_api.application.analysis_execution.retry_policy import (
    FixedDelayAnalysisExecutionRetryPolicy,
)
from incrementality_api.application.analysis_execution.settle_execution import (
    MarkAnalysisExecutionFailed,
    MarkAnalysisExecutionSucceeded,
    PersistAnalysisExecutionSuccess,
    RecordAnalysisExecutionFailure,
)
from incrementality_api.domain.analysis_results.entities import AnalysisResult
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)
from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)

APPLICATION_VERSION = "0.1.0"
SOURCE_REVISION = "a" * 40

CREATED_AT = datetime(2026, 7, 18, 10, 0, tzinfo=UTC)
AVAILABLE_AT = CREATED_AT + timedelta(minutes=1)
STARTED_AT = CREATED_AT + timedelta(minutes=2)
SETTLED_AT = CREATED_AT + timedelta(minutes=3)
RETRY_AT = CREATED_AT + timedelta(minutes=8)


class FixedClock:
    def now(self) -> datetime:
        return SETTLED_AT


class FakeRetryPolicy:
    def __init__(self, next_attempt_at: datetime | None) -> None:
        self._next_attempt_at = next_attempt_at
        self.received: tuple[AnalysisExecutionJob, datetime] | None = None

    def next_attempt_at(
        self,
        *,
        job: AnalysisExecutionJob,
        failed_at: datetime,
    ) -> datetime | None:
        self.received = (job, failed_at)
        return self._next_attempt_at


def build_running_pair(
    *,
    attempt_count: int = 1,
    max_attempts: int = 3,
) -> tuple[AnalysisExecutionJob, AnalysisRun]:
    run = AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256="c" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=1,
        semantic_mapping_snapshot=SemanticMappingSnapshot.create(
            time_column="date",
            unit_column="market",
            treatment_column="treated",
            outcome_column="revenue",
            spend_column=None,
            covariate_columns=(),
            treatment_value="true",
            control_value="false",
        ),
        created_by_user_id=uuid4(),
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        estimator_version="did-v1",
        random_seed=1_729,
        configuration_json='{"alpha":0.05}',
        created_at=CREATED_AT,
        application_version=APPLICATION_VERSION,
        source_revision=SOURCE_REVISION,
        statistical_library_versions={"numpy": "2.3.1", "statsmodels": "0.14.5"},
    ).start(started_at=STARTED_AT)

    job = AnalysisExecutionJob.enqueue(
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        analysis_run_id=run.id,
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=max_attempts,
    )

    for index in range(attempt_count):
        job = job.claim(claimed_at=STARTED_AT + timedelta(seconds=index))
        if index < attempt_count - 1:
            job = job.retry(
                failed_at=STARTED_AT + timedelta(seconds=index, microseconds=1),
                available_at=STARTED_AT + timedelta(seconds=index + 1),
                error="Temporary estimator failure.",
            )

    return job, run


class FakeJobRepository:
    def __init__(self, job: AnalysisExecutionJob | None) -> None:
        self._job = job
        self.updated: list[AnalysisExecutionJob] = []

    async def get_by_id_for_update(self, job_id: UUID) -> AnalysisExecutionJob | None:
        if self._job is None or self._job.id != job_id:
            return None
        return self._job

    async def update(self, job: AnalysisExecutionJob) -> None:
        self.updated.append(job)


class FakeRunRepository:
    def __init__(
        self,
        run: AnalysisRun | None,
        *,
        update_error: Exception | None = None,
    ) -> None:
        self._run = run
        self._update_error = update_error
        self.updated: list[AnalysisRun] = []

    async def get_by_scope_for_update(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisRun | None:
        if self._run is None:
            return None
        if (
            self._run.workspace_id,
            self._run.project_id,
            self._run.id,
        ) != (workspace_id, project_id, analysis_run_id):
            return None
        return self._run

    async def update(self, run: AnalysisRun) -> None:
        if self._update_error is not None:
            raise self._update_error
        self.updated.append(run)


class FakeResultRepository:
    def __init__(self, add_error: Exception | None = None) -> None:
        self._add_error = add_error
        self.added: list[AnalysisResult] = []

    async def add(self, result: AnalysisResult) -> None:
        if self._add_error is not None:
            raise self._add_error
        self.added.append(result)


class FakeUnitOfWork:
    def __init__(
        self,
        *,
        job: AnalysisExecutionJob | None,
        run: AnalysisRun | None,
        run_update_error: Exception | None = None,
        result_add_error: Exception | None = None,
    ) -> None:
        self.execution_jobs = FakeJobRepository(job)
        self.analysis_runs = FakeRunRepository(
            run,
            update_error=run_update_error,
        )
        self.analysis_results = FakeResultRepository(result_add_error)
        self.commit_count = 0
        self.exit_exception_type: type[BaseException] | None = None

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback
        self.exit_exception_type = exception_type

    async def commit(self) -> None:
        self.commit_count += 1


@pytest.mark.asyncio
async def test_success_marks_job_and_run_succeeded_in_one_transaction() -> None:
    job, run = build_running_pair()
    unit_of_work = FakeUnitOfWork(job=job, run=run)

    result = await MarkAnalysisExecutionSucceeded(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute(job.id)

    assert result.status is AnalysisExecutionJobStatus.SUCCEEDED
    assert unit_of_work.execution_jobs.updated == [result]
    assert len(unit_of_work.analysis_runs.updated) == 1
    assert unit_of_work.analysis_runs.updated[0].status is AnalysisRunStatus.SUCCEEDED
    assert unit_of_work.analysis_runs.updated[0].completed_at == SETTLED_AT
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_persists_structured_result_and_success_states_in_one_transaction() -> None:
    job, run = build_running_pair()
    unit_of_work = FakeUnitOfWork(job=job, run=run)
    estimation = AnalysisEstimationResult(
        effect=5.0,
        standard_error=0.5,
        p_value=0.01,
        confidence_interval_low=4.0,
        confidence_interval_high=6.0,
        observation_count=100,
        library_name="statsmodels",
        library_version="0.14.6",
        diagnostics={"r_squared": 0.9},
    )

    settled = await PersistAnalysisExecutionSuccess(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute(job_id=job.id, result=estimation)

    assert settled.status is AnalysisExecutionJobStatus.SUCCEEDED
    assert len(unit_of_work.analysis_results.added) == 1
    persisted = unit_of_work.analysis_results.added[0]
    assert persisted.analysis_run_id == run.id
    assert persisted.effect == 5.0
    assert persisted.estimator_version == "did-v1"
    assert unit_of_work.analysis_runs.updated[0].status is AnalysisRunStatus.SUCCEEDED
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_result_persistence_failure_prevents_success_state_updates() -> None:
    job, run = build_running_pair()
    unit_of_work = FakeUnitOfWork(
        job=job,
        run=run,
        result_add_error=RuntimeError("Result insert failed."),
    )
    estimation = AnalysisEstimationResult(
        effect=5.0,
        standard_error=0.5,
        p_value=0.01,
        confidence_interval_low=4.0,
        confidence_interval_high=6.0,
        observation_count=100,
        library_name="statsmodels",
        library_version="0.14.6",
    )

    with pytest.raises(RuntimeError, match="Result insert failed"):
        await PersistAnalysisExecutionSuccess(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(job_id=job.id, result=estimation)

    assert unit_of_work.execution_jobs.updated == []
    assert unit_of_work.analysis_runs.updated == []
    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
async def test_temporary_failure_returns_job_to_pending_and_keeps_run_running() -> None:
    job, run = build_running_pair()
    unit_of_work = FakeUnitOfWork(job=job, run=run)
    retry_policy = FakeRetryPolicy(RETRY_AT)

    result = await RecordAnalysisExecutionFailure(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
        retry_policy=retry_policy,
    ).execute(job_id=job.id, error="Database temporarily unavailable.")

    assert result.status is AnalysisExecutionJobStatus.PENDING
    assert result.available_at == RETRY_AT
    assert result.last_error == "Database temporarily unavailable."
    assert unit_of_work.analysis_runs.updated == [run]
    assert unit_of_work.analysis_runs.updated[0].status is AnalysisRunStatus.RUNNING
    assert retry_policy.received == (job, SETTLED_AT)
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_final_failure_dead_letters_job_and_marks_run_failed() -> None:
    job, run = build_running_pair(attempt_count=3, max_attempts=3)
    unit_of_work = FakeUnitOfWork(job=job, run=run)

    result = await MarkAnalysisExecutionFailed(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute(job_id=job.id, error="Estimator input is invalid.")

    assert result.status is AnalysisExecutionJobStatus.DEAD_LETTER
    assert unit_of_work.execution_jobs.updated == [result]
    assert len(unit_of_work.analysis_runs.updated) == 1
    failed_run = unit_of_work.analysis_runs.updated[0]
    assert failed_run.status is AnalysisRunStatus.FAILED
    assert failed_run.failure_reason == "Estimator input is invalid."
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_exhausted_retry_dead_letters_job_and_marks_run_failed() -> None:
    job, run = build_running_pair(attempt_count=3, max_attempts=3)
    unit_of_work = FakeUnitOfWork(job=job, run=run)

    result = await RecordAnalysisExecutionFailure(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
        retry_policy=FixedDelayAnalysisExecutionRetryPolicy(
            retry_delay_seconds=30,
        ),
    ).execute(job_id=job.id, error="Warehouse remained unavailable.")

    assert result.status is AnalysisExecutionJobStatus.DEAD_LETTER
    assert unit_of_work.analysis_runs.updated[0].status is AnalysisRunStatus.FAILED
    assert unit_of_work.commit_count == 1


def test_retry_policy_requires_positive_delay() -> None:
    with pytest.raises(ValueError, match="Retry delay must be positive"):
        FixedDelayAnalysisExecutionRetryPolicy(retry_delay_seconds=0)


@pytest.mark.asyncio
async def test_missing_job_raises_explicit_application_error() -> None:
    unit_of_work = FakeUnitOfWork(job=None, run=None)

    with pytest.raises(
        AnalysisExecutionJobUnavailableError,
        match="Execution job is unavailable",
    ):
        await MarkAnalysisExecutionSucceeded(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(uuid4())

    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
async def test_missing_run_raises_explicit_application_error() -> None:
    job, _run = build_running_pair()
    unit_of_work = FakeUnitOfWork(job=job, run=None)

    with pytest.raises(
        AnalysisExecutionRunUnavailableError,
        match="Analysis run is unavailable",
    ):
        await MarkAnalysisExecutionSucceeded(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(job.id)

    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
async def test_second_update_failure_prevents_settlement_commit() -> None:
    job, run = build_running_pair()
    unit_of_work = FakeUnitOfWork(
        job=job,
        run=run,
        run_update_error=RuntimeError("Run update failed."),
    )

    with pytest.raises(RuntimeError, match="Run update failed"):
        await MarkAnalysisExecutionSucceeded(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(job.id)

    assert len(unit_of_work.execution_jobs.updated) == 1
    assert unit_of_work.analysis_runs.updated == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.exit_exception_type is RuntimeError
