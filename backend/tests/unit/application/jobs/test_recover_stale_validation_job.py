from datetime import UTC, datetime, timedelta
from types import TracebackType
from uuid import uuid4

import pytest

from incrementality_api.application.jobs.recover_stale_validation_job import (
    RecoverStaleDatasetValidationJob,
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
    16,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    15,
    16,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    15,
    16,
    2,
    tzinfo=UTC,
)

CURRENT_TIME = datetime(
    2026,
    7,
    15,
    16,
    12,
    tzinfo=UTC,
)

CLAIM_TIMEOUT_SECONDS = 300

EXPECTED_CUTOFF = CURRENT_TIME - timedelta(seconds=CLAIM_TIMEOUT_SECONDS)

RECOVERY_ERROR = "Worker claim expired before completion."


class FixedClock:
    def now(self) -> datetime:
        return CURRENT_TIME


class FakeValidationJobRepository:
    def __init__(
        self,
        job: DatasetValidationJob | None,
    ) -> None:
        self._job = job
        self.claimed_before_values: list[datetime] = []
        self.updated_jobs: list[DatasetValidationJob] = []

    async def get_stale_running_for_update(
        self,
        *,
        claimed_before: datetime,
    ) -> DatasetValidationJob | None:
        self.claimed_before_values.append(
            claimed_before,
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
    ) -> None:
        self.validation_jobs = FakeValidationJobRepository(job)
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
async def test_returns_none_when_no_stale_claim_exists() -> None:
    unit_of_work = FakeValidationJobUnitOfWork(
        None,
    )

    result = await RecoverStaleDatasetValidationJob(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
        claim_timeout_seconds=(CLAIM_TIMEOUT_SECONDS),
    ).execute()

    assert result is None

    assert unit_of_work.validation_jobs.claimed_before_values == [EXPECTED_CUTOFF]
    assert unit_of_work.validation_jobs.updated_jobs == []
    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
async def test_requeues_abandoned_job_when_attempts_remain() -> None:
    running = build_running_job(
        max_attempts=3,
    )

    unit_of_work = FakeValidationJobUnitOfWork(
        running,
    )

    result = await RecoverStaleDatasetValidationJob(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
        claim_timeout_seconds=(CLAIM_TIMEOUT_SECONDS),
    ).execute()

    assert result is not None
    assert result.status is (DatasetValidationJobStatus.PENDING)
    assert result.attempt_count == 1
    assert result.claimed_at is None
    assert result.completed_at is None
    assert result.available_at == CURRENT_TIME
    assert result.last_error == RECOVERY_ERROR

    assert unit_of_work.validation_jobs.updated_jobs == [result]
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_dead_letters_abandoned_final_attempt() -> None:
    running = build_running_job(
        max_attempts=1,
    )

    unit_of_work = FakeValidationJobUnitOfWork(
        running,
    )

    result = await RecoverStaleDatasetValidationJob(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
        claim_timeout_seconds=(CLAIM_TIMEOUT_SECONDS),
    ).execute()

    assert result is not None
    assert result.status is (DatasetValidationJobStatus.DEAD_LETTER)
    assert result.claimed_at == CLAIMED_AT
    assert result.completed_at == CURRENT_TIME
    assert result.last_error == RECOVERY_ERROR
    assert unit_of_work.commit_count == 1


def test_claim_timeout_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="Claim timeout must be positive",
    ):
        RecoverStaleDatasetValidationJob(
            unit_of_work=(FakeValidationJobUnitOfWork(None)),
            clock=FixedClock(),
            claim_timeout_seconds=0,
        )
