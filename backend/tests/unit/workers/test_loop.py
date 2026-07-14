from datetime import UTC, datetime
from uuid import uuid4

import pytest

from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)
from incrementality_api.workers.loop import (
    AnalysisExecutionWorker,
    DatasetValidationWorker,
)

CREATED_AT = datetime(
    2026,
    7,
    15,
    15,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    15,
    15,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    15,
    15,
    2,
    tzinfo=UTC,
)

COMPLETED_AT = datetime(
    2026,
    7,
    15,
    15,
    3,
    tzinfo=UTC,
)


class StopWorker(BaseException):
    pass


class FakeProcessNext:
    def __init__(
        self,
        results: list[DatasetValidationJob | None | BaseException],
    ) -> None:
        self._results = list(results)
        self.call_count = 0

    async def execute(
        self,
    ) -> DatasetValidationJob | None:
        self.call_count += 1
        result = self._results.pop(0)

        if isinstance(result, BaseException):
            raise result

        return result


class FakeSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(
        self,
        delay: float,
    ) -> None:
        self.delays.append(delay)


class FakeAnalysisProcessNext:
    def __init__(self, results: list[AnalysisExecutionJob | None | BaseException]) -> None:
        self._results = list(results)

    async def execute(self) -> AnalysisExecutionJob | None:
        result = self._results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def build_succeeded_job() -> DatasetValidationJob:
    return (
        DatasetValidationJob.enqueue(
            workspace_id=uuid4(),
            project_id=uuid4(),
            dataset_id=uuid4(),
            created_at=CREATED_AT,
            available_at=AVAILABLE_AT,
            max_attempts=3,
        )
        .claim(
            claimed_at=CLAIMED_AT,
        )
        .mark_succeeded(
            completed_at=COMPLETED_AT,
        )
    )


def build_succeeded_analysis_job() -> AnalysisExecutionJob:
    return (
        AnalysisExecutionJob.enqueue(
            workspace_id=uuid4(),
            project_id=uuid4(),
            analysis_run_id=uuid4(),
            created_at=CREATED_AT,
            available_at=AVAILABLE_AT,
        )
        .claim(claimed_at=CLAIMED_AT)
        .mark_succeeded(completed_at=COMPLETED_AT)
    )


@pytest.mark.asyncio
async def test_analysis_worker_polls_and_returns_processed_job() -> None:
    job = build_succeeded_analysis_job()
    sleeper = FakeSleeper()
    worker = AnalysisExecutionWorker(
        process_next=FakeAnalysisProcessNext([job]),
        sleep=sleeper.sleep,
        poll_interval_seconds=0.25,
        error_retry_seconds=2.0,
    )

    assert await worker.run_once() == job
    assert sleeper.delays == []


@pytest.mark.asyncio
async def test_analysis_worker_propagates_cancellation_for_graceful_shutdown() -> None:
    worker = AnalysisExecutionWorker(
        process_next=FakeAnalysisProcessNext([StopWorker()]),
        sleep=FakeSleeper().sleep,
    )

    with pytest.raises(StopWorker):
        await worker.run_forever()


@pytest.mark.asyncio
async def test_run_once_returns_processed_job_without_sleeping() -> None:
    job = build_succeeded_job()
    process_next = FakeProcessNext([job])
    sleeper = FakeSleeper()

    result = await DatasetValidationWorker(
        process_next=process_next,
        sleep=sleeper.sleep,
        poll_interval_seconds=0.25,
        error_retry_seconds=2.0,
    ).run_once()

    assert result == job
    assert process_next.call_count == 1
    assert sleeper.delays == []


@pytest.mark.asyncio
async def test_empty_queue_waits_before_polling_again() -> None:
    process_next = FakeProcessNext([None])
    sleeper = FakeSleeper()

    result = await DatasetValidationWorker(
        process_next=process_next,
        sleep=sleeper.sleep,
        poll_interval_seconds=0.25,
        error_retry_seconds=2.0,
    ).run_once()

    assert result is None
    assert process_next.call_count == 1
    assert sleeper.delays == [0.25]


@pytest.mark.asyncio
async def test_unexpected_failure_uses_error_backoff() -> None:
    process_next = FakeProcessNext([RuntimeError("Database temporarily unavailable.")])
    sleeper = FakeSleeper()

    result = await DatasetValidationWorker(
        process_next=process_next,
        sleep=sleeper.sleep,
        poll_interval_seconds=0.25,
        error_retry_seconds=2.0,
    ).run_once()

    assert result is None
    assert process_next.call_count == 1
    assert sleeper.delays == [2.0]


def test_poll_interval_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="Poll interval must be positive",
    ):
        DatasetValidationWorker(
            process_next=FakeProcessNext([]),
            sleep=FakeSleeper().sleep,
            poll_interval_seconds=0,
            error_retry_seconds=2.0,
        )


def test_error_retry_delay_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="Error retry delay must be positive",
    ):
        DatasetValidationWorker(
            process_next=FakeProcessNext([]),
            sleep=FakeSleeper().sleep,
            poll_interval_seconds=0.25,
            error_retry_seconds=0,
        )


@pytest.mark.asyncio
async def test_run_forever_repeatedly_processes_jobs() -> None:
    job = build_succeeded_job()

    process_next = FakeProcessNext(
        [
            None,
            job,
            StopWorker(),
        ]
    )
    sleeper = FakeSleeper()

    worker = DatasetValidationWorker(
        process_next=process_next,
        sleep=sleeper.sleep,
        poll_interval_seconds=0.25,
        error_retry_seconds=2.0,
    )

    with pytest.raises(StopWorker):
        await worker.run_forever()

    assert process_next.call_count == 3
    assert sleeper.delays == [0.25]
