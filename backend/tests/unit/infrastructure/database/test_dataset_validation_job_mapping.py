from datetime import UTC, datetime, timedelta
from uuid import uuid4

from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)
from incrementality_api.domain.jobs.status import (
    DatasetValidationJobStatus,
)
from incrementality_api.infrastructure.database.repositories.jobs import (
    to_dataset_validation_job_entity,
    to_dataset_validation_job_model,
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

FAILED_AT = datetime(
    2026,
    7,
    15,
    10,
    3,
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


def build_pending_job() -> DatasetValidationJob:
    return DatasetValidationJob.enqueue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=3,
    )


def round_trip(
    job: DatasetValidationJob,
) -> DatasetValidationJob:
    model = to_dataset_validation_job_model(job)

    assert model.id == job.id
    assert model.workspace_id == job.workspace_id
    assert model.project_id == job.project_id
    assert model.dataset_id == job.dataset_id
    assert model.status == job.status.value
    assert model.attempt_count == job.attempt_count
    assert model.max_attempts == job.max_attempts
    assert model.available_at == job.available_at
    assert model.created_at == job.created_at
    assert model.claimed_at == job.claimed_at
    assert model.completed_at == job.completed_at
    assert model.last_error == job.last_error

    return to_dataset_validation_job_entity(model)


def test_round_trips_initial_pending_job() -> None:
    job = build_pending_job()

    result = round_trip(job)

    assert result == job
    assert result.status is DatasetValidationJobStatus.PENDING
    assert result.attempt_count == 0
    assert result.last_error is None


def test_round_trips_running_job() -> None:
    job = build_pending_job().claim(
        claimed_at=CLAIMED_AT,
    )

    result = round_trip(job)

    assert result == job
    assert result.status is DatasetValidationJobStatus.RUNNING
    assert result.attempt_count == 1
    assert result.claimed_at == CLAIMED_AT


def test_round_trips_retry_pending_job() -> None:
    job = (
        build_pending_job()
        .claim(
            claimed_at=CLAIMED_AT,
        )
        .retry(
            failed_at=FAILED_AT,
            available_at=(FAILED_AT + timedelta(minutes=1)),
            error="S3 temporarily unavailable.",
        )
    )

    result = round_trip(job)

    assert result == job
    assert result.status is DatasetValidationJobStatus.PENDING
    assert result.attempt_count == 1
    assert result.claimed_at is None
    assert result.completed_at is None
    assert result.last_error == ("S3 temporarily unavailable.")


def test_round_trips_succeeded_job() -> None:
    job = (
        build_pending_job()
        .claim(
            claimed_at=CLAIMED_AT,
        )
        .mark_succeeded(
            completed_at=COMPLETED_AT,
        )
    )

    result = round_trip(job)

    assert result == job
    assert result.status is (DatasetValidationJobStatus.SUCCEEDED)
    assert result.completed_at == COMPLETED_AT
    assert result.last_error is None


def test_round_trips_dead_letter_job() -> None:
    job = (
        build_pending_job()
        .claim(
            claimed_at=CLAIMED_AT,
        )
        .mark_dead_letter(
            completed_at=COMPLETED_AT,
            error="S3 remained unavailable.",
        )
    )

    result = round_trip(job)

    assert result == job
    assert result.status is (DatasetValidationJobStatus.DEAD_LETTER)
    assert result.completed_at == COMPLETED_AT
    assert result.last_error == ("S3 remained unavailable.")
