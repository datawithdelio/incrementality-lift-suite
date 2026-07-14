from datetime import UTC, datetime, timedelta
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.jobs.errors import (
    ValidationJobUnavailableError,
)
from incrementality_api.application.jobs.settle_validation_job import (
    MarkDatasetValidationJobSucceeded,
    RecordDatasetValidationJobFailure,
)
from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)
from incrementality_api.domain.jobs.status import (
    DatasetValidationJobStatus,
)

CREATED_AT = datetime(
    2026,
    7,
    15,
    13,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    15,
    13,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    15,
    13,
    2,
    tzinfo=UTC,
)

SETTLED_AT = datetime(
    2026,
    7,
    15,
    13,
    3,
    tzinfo=UTC,
)


class FixedClock:
    def now(self) -> datetime:
        return SETTLED_AT


class FakeValidationJobRepository:
    def __init__(
        self,
        job: DatasetValidationJob | None,
    ) -> None:
        self._job = job
        self.requested_job_ids: list[UUID] = []
        self.updated_jobs: list[DatasetValidationJob] = []

    async def get_by_id_for_update(
        self,
        job_id: UUID,
    ) -> DatasetValidationJob | None:
        self.requested_job_ids.append(job_id)
        return self._job

    async def update(
        self,
        job: DatasetValidationJob,
    ) -> None:
        self.updated_jobs.append(job)


class FakeValidationJobUnitOfWork:
    def __init__(
        self,
        job: DatasetValidationJob | None,
        *,
        commit_error: Exception | None = None,
    ) -> None:
        self.validation_jobs = FakeValidationJobRepository(job)
        self._commit_error = commit_error
        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeValidationJobUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback

        if exception_type is not None:
            self.rollback_count += 1

    async def commit(self) -> None:
        self.commit_count += 1

        if self._commit_error is not None:
            raise self._commit_error

    async def rollback(self) -> None:
        self.rollback_count += 1


def build_running_job(
    *,
    max_attempts: int = 3,
) -> DatasetValidationJob:
    return DatasetValidationJob.enqueue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=max_attempts,
    ).claim(
        claimed_at=CLAIMED_AT,
    )


@pytest.mark.asyncio
async def test_marks_claimed_job_succeeded() -> None:
    running = build_running_job()
    unit_of_work = FakeValidationJobUnitOfWork(
        running,
    )

    result = await MarkDatasetValidationJobSucceeded(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute(running.id)

    assert result.status is (DatasetValidationJobStatus.SUCCEEDED)
    assert result.completed_at == SETTLED_AT
    assert result.last_error is None

    assert unit_of_work.validation_jobs.requested_job_ids == [running.id]
    assert unit_of_work.validation_jobs.updated_jobs == [result]
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_requeues_failure_when_attempts_remain() -> None:
    running = build_running_job(
        max_attempts=3,
    )
    unit_of_work = FakeValidationJobUnitOfWork(
        running,
    )

    result = await RecordDatasetValidationJobFailure(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
        retry_delay_seconds=45,
    ).execute(
        job_id=running.id,
        error="S3 temporarily unavailable.",
    )

    assert result.status is (DatasetValidationJobStatus.PENDING)
    assert result.attempt_count == 1
    assert result.claimed_at is None
    assert result.completed_at is None
    assert result.available_at == (SETTLED_AT + timedelta(seconds=45))
    assert result.last_error == ("S3 temporarily unavailable.")
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_dead_letters_failure_when_attempts_exhausted() -> None:
    running = build_running_job(
        max_attempts=1,
    )
    unit_of_work = FakeValidationJobUnitOfWork(
        running,
    )

    result = await RecordDatasetValidationJobFailure(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
        retry_delay_seconds=45,
    ).execute(
        job_id=running.id,
        error="S3 remained unavailable.",
    )

    assert result.status is (DatasetValidationJobStatus.DEAD_LETTER)
    assert result.completed_at == SETTLED_AT
    assert result.claimed_at == CLAIMED_AT
    assert result.last_error == ("S3 remained unavailable.")
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_missing_job_cannot_be_settled() -> None:
    missing_job_id = uuid4()
    unit_of_work = FakeValidationJobUnitOfWork(
        None,
    )

    with pytest.raises(
        ValidationJobUnavailableError,
        match="Validation job is unavailable",
    ):
        await MarkDatasetValidationJobSucceeded(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(missing_job_id)

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_commit_failure_rolls_back_settlement() -> None:
    running = build_running_job()

    unit_of_work = FakeValidationJobUnitOfWork(
        running,
        commit_error=RuntimeError(
            "Database commit failed.",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Database commit failed",
    ):
        await MarkDatasetValidationJobSucceeded(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(running.id)

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 1


def test_retry_delay_must_be_positive() -> None:
    running = build_running_job()

    with pytest.raises(
        ValueError,
        match="Retry delay must be positive",
    ):
        RecordDatasetValidationJobFailure(
            unit_of_work=(FakeValidationJobUnitOfWork(running)),
            clock=FixedClock(),
            retry_delay_seconds=0,
        )
