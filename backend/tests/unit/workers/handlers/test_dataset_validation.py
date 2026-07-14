from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.datasets.validate_dataset import (
    ValidateDatasetCommand,
)
from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)
from incrementality_api.domain.jobs.status import (
    DatasetValidationJobStatus,
)
from incrementality_api.workers.handlers.dataset_validation import (
    RunNextDatasetValidationJob,
)

CREATED_AT = datetime(
    2026,
    7,
    15,
    14,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    15,
    14,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    15,
    14,
    2,
    tzinfo=UTC,
)

SETTLED_AT = datetime(
    2026,
    7,
    15,
    14,
    3,
    tzinfo=UTC,
)


class FakeClaimNext:
    def __init__(
        self,
        job: DatasetValidationJob | None,
    ) -> None:
        self._job = job
        self.call_count = 0

    async def execute(
        self,
    ) -> DatasetValidationJob | None:
        self.call_count += 1
        return self._job


class FakeValidateDataset:
    def __init__(
        self,
        *,
        result: object = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.commands: list[ValidateDatasetCommand] = []

    async def execute(
        self,
        command: ValidateDatasetCommand,
    ) -> object:
        self.commands.append(command)

        if self._error is not None:
            raise self._error

        return self._result


class FakeMarkSucceeded:
    def __init__(
        self,
        result: DatasetValidationJob,
    ) -> None:
        self._result = result
        self.job_ids: list[UUID] = []

    async def execute(
        self,
        job_id: UUID,
    ) -> DatasetValidationJob:
        self.job_ids.append(job_id)
        return self._result


class FakeRecordFailure:
    def __init__(
        self,
        result: DatasetValidationJob,
    ) -> None:
        self._result = result
        self.calls: list[tuple[UUID, str]] = []

    async def execute(
        self,
        *,
        job_id: UUID,
        error: str,
    ) -> DatasetValidationJob:
        self.calls.append(
            (
                job_id,
                error,
            )
        )
        return self._result


class EmptyMessageInfrastructureError(Exception):
    pass


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


def build_succeeded_job(
    running: DatasetValidationJob,
) -> DatasetValidationJob:
    return running.mark_succeeded(
        completed_at=SETTLED_AT,
    )


def build_retry_job(
    running: DatasetValidationJob,
    *,
    error: str,
) -> DatasetValidationJob:
    return running.retry(
        failed_at=SETTLED_AT,
        available_at=(SETTLED_AT + timedelta(seconds=30)),
        error=error,
    )


@pytest.mark.asyncio
async def test_returns_none_when_queue_is_empty() -> None:
    claim_next = FakeClaimNext(None)
    validate_dataset = FakeValidateDataset()
    mark_succeeded = FakeMarkSucceeded(
        build_succeeded_job(build_running_job()),
    )
    record_failure = FakeRecordFailure(
        build_retry_job(
            build_running_job(),
            error="unused",
        )
    )

    result = await RunNextDatasetValidationJob(
        claim_next=claim_next,
        validate_dataset=validate_dataset,
        mark_succeeded=mark_succeeded,
        record_failure=record_failure,
    ).execute()

    assert result is None
    assert claim_next.call_count == 1
    assert validate_dataset.commands == []
    assert mark_succeeded.job_ids == []
    assert record_failure.calls == []


@pytest.mark.asyncio
async def test_validates_claimed_job_and_marks_it_succeeded() -> None:
    running = build_running_job()
    succeeded = build_succeeded_job(running)

    validate_dataset = FakeValidateDataset(
        result=object(),
    )
    mark_succeeded = FakeMarkSucceeded(
        succeeded,
    )
    record_failure = FakeRecordFailure(
        build_retry_job(
            running,
            error="unused",
        )
    )

    result = await RunNextDatasetValidationJob(
        claim_next=FakeClaimNext(running),
        validate_dataset=validate_dataset,
        mark_succeeded=mark_succeeded,
        record_failure=record_failure,
    ).execute()

    assert result == succeeded
    assert result.status is (DatasetValidationJobStatus.SUCCEEDED)

    assert validate_dataset.commands == [
        ValidateDatasetCommand(
            workspace_id=running.workspace_id,
            project_id=running.project_id,
            dataset_id=running.dataset_id,
        )
    ]
    assert mark_succeeded.job_ids == [running.id]
    assert record_failure.calls == []


@pytest.mark.asyncio
async def test_failed_dataset_outcome_still_completes_job() -> None:
    running = build_running_job()
    succeeded = build_succeeded_job(running)

    validate_dataset = FakeValidateDataset(
        result="dataset-failed-content-validation",
    )
    mark_succeeded = FakeMarkSucceeded(
        succeeded,
    )
    record_failure = FakeRecordFailure(
        build_retry_job(
            running,
            error="unused",
        )
    )

    result = await RunNextDatasetValidationJob(
        claim_next=FakeClaimNext(running),
        validate_dataset=validate_dataset,
        mark_succeeded=mark_succeeded,
        record_failure=record_failure,
    ).execute()

    assert result == succeeded
    assert mark_succeeded.job_ids == [running.id]
    assert record_failure.calls == []


@pytest.mark.asyncio
async def test_infrastructure_failure_is_recorded_for_retry() -> None:
    running = build_running_job()
    retry = build_retry_job(
        running,
        error="S3 temporarily unavailable.",
    )

    mark_succeeded = FakeMarkSucceeded(
        build_succeeded_job(running),
    )
    record_failure = FakeRecordFailure(
        retry,
    )

    result = await RunNextDatasetValidationJob(
        claim_next=FakeClaimNext(running),
        validate_dataset=FakeValidateDataset(
            error=RuntimeError("S3 temporarily unavailable."),
        ),
        mark_succeeded=mark_succeeded,
        record_failure=record_failure,
    ).execute()

    assert result == retry
    assert result.status is (DatasetValidationJobStatus.PENDING)
    assert mark_succeeded.job_ids == []
    assert record_failure.calls == [
        (
            running.id,
            "S3 temporarily unavailable.",
        )
    ]


@pytest.mark.asyncio
async def test_blank_exception_uses_exception_class_name() -> None:
    running = build_running_job()
    retry = build_retry_job(
        running,
        error="EmptyMessageInfrastructureError",
    )

    record_failure = FakeRecordFailure(
        retry,
    )

    result = await RunNextDatasetValidationJob(
        claim_next=FakeClaimNext(running),
        validate_dataset=FakeValidateDataset(
            error=EmptyMessageInfrastructureError(),
        ),
        mark_succeeded=FakeMarkSucceeded(
            build_succeeded_job(running),
        ),
        record_failure=record_failure,
    ).execute()

    assert result == retry
    assert record_failure.calls == [
        (
            running.id,
            "EmptyMessageInfrastructureError",
        )
    ]
