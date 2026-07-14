from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
    AnalysisEstimatorInput,
    PermanentEstimationError,
    RetryableEstimationError,
    UnsupportedEstimatorTypeError,
)
from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)
from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.workers.handlers.analysis_execution import (
    RunNextAnalysisExecutionJob,
)

CREATED_AT = datetime(2026, 7, 19, 10, 0, tzinfo=UTC)
CLAIMED_AT = CREATED_AT + timedelta(minutes=1)
SETTLED_AT = CREATED_AT + timedelta(minutes=2)


def build_running_job() -> AnalysisExecutionJob:
    return AnalysisExecutionJob.enqueue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        analysis_run_id=uuid4(),
        created_at=CREATED_AT,
        available_at=CREATED_AT,
    ).claim(claimed_at=CLAIMED_AT)


def settle_succeeded(job: AnalysisExecutionJob) -> AnalysisExecutionJob:
    return job.mark_succeeded(completed_at=SETTLED_AT)


def settle_retry(job: AnalysisExecutionJob, error: str) -> AnalysisExecutionJob:
    return job.retry(
        failed_at=SETTLED_AT,
        available_at=SETTLED_AT + timedelta(seconds=30),
        error=error,
    )


def settle_failed(job: AnalysisExecutionJob, error: str) -> AnalysisExecutionJob:
    return job.mark_dead_letter(completed_at=SETTLED_AT, error=error)


class FakeClaimNext:
    def __init__(self, job: AnalysisExecutionJob | None) -> None:
        self._job = job

    async def execute(self) -> AnalysisExecutionJob | None:
        return self._job


class FakeInputLoader:
    def __init__(
        self,
        estimator_input: AnalysisEstimatorInput | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._input = estimator_input
        self._error = error
        self.job_ids: list[UUID] = []

    async def load(self, job: AnalysisExecutionJob) -> AnalysisEstimatorInput:
        self.job_ids.append(job.id)
        if self._error is not None:
            raise self._error
        assert self._input is not None
        return self._input


class FakeEstimator:
    def __init__(
        self,
        result: AnalysisEstimationResult | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.inputs: list[object] = []

    def estimate(self, estimator_input: object) -> AnalysisEstimationResult:
        self.inputs.append(estimator_input)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class FakeSelector:
    def __init__(
        self,
        estimator: FakeEstimator | None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._estimator = estimator
        self._error = error
        self.received: list[AnalysisEstimatorType] = []

    def select(self, estimator_type: AnalysisEstimatorType) -> FakeEstimator:
        self.received.append(estimator_type)
        if self._error is not None:
            raise self._error
        assert self._estimator is not None
        return self._estimator


class FakeResultSink:
    def __init__(self) -> None:
        self.saved: list[tuple[AnalysisExecutionJob, AnalysisEstimationResult]] = []

    async def save(
        self,
        *,
        job: AnalysisExecutionJob,
        result: AnalysisEstimationResult,
    ) -> None:
        self.saved.append((job, result))


@dataclass
class FakeMarkSucceeded:
    result: AnalysisExecutionJob

    def __post_init__(self) -> None:
        self.job_ids: list[UUID] = []

    async def execute(self, job_id: UUID) -> AnalysisExecutionJob:
        self.job_ids.append(job_id)
        return self.result


@dataclass
class FakeRecordRetryableFailure:
    result: AnalysisExecutionJob

    def __post_init__(self) -> None:
        self.calls: list[tuple[UUID, str]] = []

    async def execute(self, *, job_id: UUID, error: str) -> AnalysisExecutionJob:
        self.calls.append((job_id, error))
        return self.result


@dataclass
class FakeMarkFailed:
    result: AnalysisExecutionJob

    def __post_init__(self) -> None:
        self.calls: list[tuple[UUID, str]] = []

    async def execute(self, *, job_id: UUID, error: str) -> AnalysisExecutionJob:
        self.calls.append((job_id, error))
        return self.result


def build_input() -> AnalysisEstimatorInput:
    return AnalysisEstimatorInput(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        payload=object(),
    )


def build_result() -> AnalysisEstimationResult:
    return AnalysisEstimationResult(
        effect=5.0,
        standard_error=0.5,
        p_value=0.01,
        confidence_interval_low=4.0,
        confidence_interval_high=6.0,
        observation_count=100,
    )


def build_processor(
    *,
    job: AnalysisExecutionJob,
    loader: FakeInputLoader,
    selector: FakeSelector,
) -> tuple[
    RunNextAnalysisExecutionJob,
    FakeResultSink,
    FakeMarkSucceeded,
    FakeRecordRetryableFailure,
    FakeMarkFailed,
]:
    sink = FakeResultSink()
    mark_succeeded = FakeMarkSucceeded(settle_succeeded(job))
    record_retry = FakeRecordRetryableFailure(settle_retry(job, "retry"))
    mark_failed = FakeMarkFailed(settle_failed(job, "failed"))
    processor = RunNextAnalysisExecutionJob(
        claim_next=FakeClaimNext(job),
        input_loader=loader,
        estimator_selector=selector,
        result_sink=sink,
        mark_succeeded=mark_succeeded,
        record_retryable_failure=record_retry,
        mark_failed=mark_failed,
    )
    return processor, sink, mark_succeeded, record_retry, mark_failed


@pytest.mark.asyncio
async def test_successful_estimation_saves_result_then_settles_success() -> None:
    job = build_running_job()
    estimator_input = build_input()
    result = build_result()
    estimator = FakeEstimator(result)
    processor, sink, mark_succeeded, record_retry, mark_failed = build_processor(
        job=job,
        loader=FakeInputLoader(estimator_input),
        selector=FakeSelector(estimator),
    )

    settled = await processor.execute()

    assert settled is not None
    assert settled.status is AnalysisExecutionJobStatus.SUCCEEDED
    assert estimator.inputs == [estimator_input.payload]
    assert sink.saved == [(job, result)]
    assert mark_succeeded.job_ids == [job.id]
    assert record_retry.calls == []
    assert mark_failed.calls == []


@pytest.mark.asyncio
async def test_retryable_estimator_error_schedules_retry() -> None:
    job = build_running_job()
    error = RetryableEstimationError("Warehouse timed out.")
    processor, sink, mark_succeeded, record_retry, mark_failed = build_processor(
        job=job,
        loader=FakeInputLoader(build_input()),
        selector=FakeSelector(FakeEstimator(error=error)),
    )

    settled = await processor.execute()

    assert settled is not None
    assert settled.status is AnalysisExecutionJobStatus.PENDING
    assert sink.saved == []
    assert mark_succeeded.job_ids == []
    assert record_retry.calls == [(job.id, "Warehouse timed out.")]
    assert mark_failed.calls == []


@pytest.mark.asyncio
async def test_permanent_estimator_error_dead_letters_execution() -> None:
    job = build_running_job()
    error = PermanentEstimationError("Treatment groups are missing.")
    processor, sink, mark_succeeded, record_retry, mark_failed = build_processor(
        job=job,
        loader=FakeInputLoader(build_input()),
        selector=FakeSelector(FakeEstimator(error=error)),
    )

    settled = await processor.execute()

    assert settled is not None
    assert settled.status is AnalysisExecutionJobStatus.DEAD_LETTER
    assert sink.saved == []
    assert mark_succeeded.job_ids == []
    assert record_retry.calls == []
    assert mark_failed.calls == [(job.id, "Treatment groups are missing.")]


@pytest.mark.asyncio
async def test_unsupported_estimator_type_dead_letters_execution() -> None:
    job = build_running_job()
    unsupported = UnsupportedEstimatorTypeError("synthetic_control is unsupported.")
    processor, _sink, _success, retry, failed = build_processor(
        job=job,
        loader=FakeInputLoader(build_input()),
        selector=FakeSelector(None, error=unsupported),
    )

    settled = await processor.execute()

    assert settled is not None
    assert settled.status is AnalysisExecutionJobStatus.DEAD_LETTER
    assert retry.calls == []
    assert failed.calls == [(job.id, "synthetic_control is unsupported.")]
