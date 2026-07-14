from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)
from incrementality_api.domain.jobs.errors import (
    InvalidJobError,
    InvalidJobTransitionError,
)
from incrementality_api.domain.jobs.status import (
    DatasetValidationJobStatus,
)

CREATED_AT = datetime(
    2026,
    7,
    15,
    10,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    15,
    10,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    15,
    10,
    2,
    tzinfo=UTC,
)

COMPLETED_AT = datetime(
    2026,
    7,
    15,
    10,
    4,
    tzinfo=UTC,
)


def enqueue_job(
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
    )


def running_job(
    *,
    max_attempts: int = 3,
) -> DatasetValidationJob:
    return enqueue_job(
        max_attempts=max_attempts,
    ).claim(
        claimed_at=CLAIMED_AT,
    )


def test_enqueues_pending_validation_job() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()

    job = DatasetValidationJob.enqueue(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=3,
    )

    assert job.workspace_id == workspace_id
    assert job.project_id == project_id
    assert job.dataset_id == dataset_id
    assert job.status is DatasetValidationJobStatus.PENDING
    assert job.attempt_count == 0
    assert job.max_attempts == 3
    assert job.available_at == AVAILABLE_AT
    assert job.created_at == CREATED_AT
    assert job.claimed_at is None
    assert job.completed_at is None
    assert job.last_error is None


def test_max_attempts_must_be_positive() -> None:
    with pytest.raises(
        InvalidJobError,
        match="Maximum attempts must be positive",
    ):
        enqueue_job(max_attempts=0)


def test_enqueue_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(
        InvalidJobError,
        match="Job timestamps must be timezone-aware",
    ):
        DatasetValidationJob.enqueue(
            workspace_id=uuid4(),
            project_id=uuid4(),
            dataset_id=uuid4(),
            created_at=datetime(2026, 7, 15, 10, 0),
            available_at=AVAILABLE_AT,
        )


def test_claims_available_pending_job() -> None:
    pending = enqueue_job()

    running = pending.claim(
        claimed_at=CLAIMED_AT,
    )

    assert running.status is DatasetValidationJobStatus.RUNNING
    assert running.attempt_count == 1
    assert running.claimed_at == CLAIMED_AT
    assert running.completed_at is None
    assert running.last_error is None

    assert pending.status is DatasetValidationJobStatus.PENDING
    assert pending.attempt_count == 0


def test_cannot_claim_job_before_available_time() -> None:
    pending = enqueue_job()

    with pytest.raises(
        InvalidJobTransitionError,
        match="Job is not available for claiming",
    ):
        pending.claim(
            claimed_at=AVAILABLE_AT - timedelta(seconds=1),
        )


def test_only_pending_job_can_be_claimed() -> None:
    running = running_job()

    with pytest.raises(
        InvalidJobTransitionError,
        match="cannot be claimed",
    ):
        running.claim(
            claimed_at=CLAIMED_AT + timedelta(seconds=1),
        )


def test_marks_running_job_succeeded() -> None:
    running = running_job()

    succeeded = running.mark_succeeded(
        completed_at=COMPLETED_AT,
    )

    assert succeeded.status is DatasetValidationJobStatus.SUCCEEDED
    assert succeeded.completed_at == COMPLETED_AT
    assert succeeded.claimed_at == CLAIMED_AT
    assert succeeded.last_error is None


def test_retries_running_job_when_attempts_remain() -> None:
    running = running_job(max_attempts=3)

    retry_at = COMPLETED_AT + timedelta(minutes=1)

    pending = running.retry(
        failed_at=COMPLETED_AT,
        available_at=retry_at,
        error="S3 temporarily unavailable.",
    )

    assert pending.status is DatasetValidationJobStatus.PENDING
    assert pending.attempt_count == 1
    assert pending.available_at == retry_at
    assert pending.claimed_at is None
    assert pending.completed_at is None
    assert pending.last_error == ("S3 temporarily unavailable.")


def test_retry_rejects_exhausted_job() -> None:
    running = running_job(max_attempts=1)

    with pytest.raises(
        InvalidJobTransitionError,
        match="has exhausted its attempts",
    ):
        running.retry(
            failed_at=COMPLETED_AT,
            available_at=(COMPLETED_AT + timedelta(minutes=1)),
            error="S3 temporarily unavailable.",
        )


def test_marks_running_job_dead_letter() -> None:
    running = running_job(max_attempts=1)

    dead_letter = running.mark_dead_letter(
        completed_at=COMPLETED_AT,
        error="S3 remained unavailable.",
    )

    assert dead_letter.status is DatasetValidationJobStatus.DEAD_LETTER
    assert dead_letter.completed_at == COMPLETED_AT
    assert dead_letter.last_error == ("S3 remained unavailable.")


def test_job_error_must_not_be_blank() -> None:
    running = running_job()

    with pytest.raises(
        InvalidJobTransitionError,
        match="Job error must not be blank",
    ):
        running.retry(
            failed_at=COMPLETED_AT,
            available_at=(COMPLETED_AT + timedelta(minutes=1)),
            error="   ",
        )


def test_completion_cannot_precede_claim() -> None:
    running = running_job()

    with pytest.raises(
        InvalidJobTransitionError,
        match=("Job completion timestamp cannot precede its claim timestamp"),
    ):
        running.mark_succeeded(
            completed_at=CLAIMED_AT - timedelta(seconds=1),
        )
