from datetime import UTC, datetime
from types import TracebackType
from uuid import uuid4

import pytest

from incrementality_api.application.jobs.claim_next_validation_job import (
    ClaimNextDatasetValidationJob,
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
    12,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    15,
    12,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    15,
    12,
    2,
    tzinfo=UTC,
)


class FixedClock:
    def now(self) -> datetime:
        return CLAIMED_AT


class FakeValidationJobRepository:
    def __init__(
        self,
        job: DatasetValidationJob | None,
    ) -> None:
        self._job = job
        self.requested_available_times: list[datetime] = []
        self.updated_jobs: list[DatasetValidationJob] = []

    async def get_next_available_for_update(
        self,
        *,
        available_at: datetime,
    ) -> DatasetValidationJob | None:
        self.requested_available_times.append(
            available_at,
        )
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


def build_pending_job() -> DatasetValidationJob:
    return DatasetValidationJob.enqueue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=3,
    )


@pytest.mark.asyncio
async def test_claims_next_available_job() -> None:
    pending = build_pending_job()
    unit_of_work = FakeValidationJobUnitOfWork(
        pending,
    )

    result = await ClaimNextDatasetValidationJob(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute()

    assert result is not None
    assert result.id == pending.id
    assert result.status is (DatasetValidationJobStatus.RUNNING)
    assert result.attempt_count == 1
    assert result.claimed_at == CLAIMED_AT

    assert unit_of_work.validation_jobs.requested_available_times == [CLAIMED_AT]
    assert unit_of_work.validation_jobs.updated_jobs == [result]
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_returns_none_when_queue_is_empty() -> None:
    unit_of_work = FakeValidationJobUnitOfWork(
        None,
    )

    result = await ClaimNextDatasetValidationJob(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute()

    assert result is None
    assert unit_of_work.validation_jobs.updated_jobs == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_commit_failure_rolls_back_claim() -> None:
    pending = build_pending_job()

    unit_of_work = FakeValidationJobUnitOfWork(
        pending,
        commit_error=RuntimeError("Database commit failed."),
    )

    with pytest.raises(
        RuntimeError,
        match="Database commit failed",
    ):
        await ClaimNextDatasetValidationJob(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute()

    assert len(unit_of_work.validation_jobs.updated_jobs) == 1
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 1
