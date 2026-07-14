from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from incrementality_api.domain.analysis_runs.execution_job_errors import (
    InvalidAnalysisExecutionJobError,
    InvalidAnalysisExecutionJobTransitionError,
)
from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)

CREATED_AT = datetime(
    2026,
    7,
    16,
    10,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    16,
    10,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    16,
    10,
    2,
    tzinfo=UTC,
)

FAILED_AT = datetime(
    2026,
    7,
    16,
    10,
    3,
    tzinfo=UTC,
)

COMPLETED_AT = datetime(
    2026,
    7,
    16,
    10,
    4,
    tzinfo=UTC,
)


def enqueue_job(
    *,
    max_attempts: int = 3,
) -> AnalysisExecutionJob:
    return AnalysisExecutionJob.enqueue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        analysis_run_id=uuid4(),
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=max_attempts,
    )


def running_job(
    *,
    max_attempts: int = 3,
) -> AnalysisExecutionJob:
    return enqueue_job(
        max_attempts=max_attempts,
    ).claim(
        claimed_at=CLAIMED_AT,
    )


def test_enqueues_pending_execution_job() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    analysis_run_id = uuid4()

    job = AnalysisExecutionJob.enqueue(
        workspace_id=workspace_id,
        project_id=project_id,
        analysis_run_id=analysis_run_id,
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=3,
    )

    assert job.workspace_id == workspace_id
    assert job.project_id == project_id
    assert job.analysis_run_id == analysis_run_id
    assert job.status is AnalysisExecutionJobStatus.PENDING
    assert job.attempt_count == 0
    assert job.max_attempts == 3
    assert job.available_at == AVAILABLE_AT
    assert job.created_at == CREATED_AT
    assert job.claimed_at is None
    assert job.completed_at is None
    assert job.last_error is None


def test_max_attempts_must_be_positive() -> None:
    with pytest.raises(
        InvalidAnalysisExecutionJobError,
        match="Maximum attempts must be positive",
    ):
        enqueue_job(
            max_attempts=0,
        )


def test_enqueue_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(
        InvalidAnalysisExecutionJobError,
        match=("Analysis execution job timestamps must be timezone-aware"),
    ):
        AnalysisExecutionJob.enqueue(
            workspace_id=uuid4(),
            project_id=uuid4(),
            analysis_run_id=uuid4(),
            created_at=datetime(
                2026,
                7,
                16,
                10,
                0,
            ),
            available_at=AVAILABLE_AT,
        )


def test_available_time_cannot_precede_creation() -> None:
    with pytest.raises(
        InvalidAnalysisExecutionJobError,
        match=("Analysis execution availability cannot precede creation"),
    ):
        AnalysisExecutionJob.enqueue(
            workspace_id=uuid4(),
            project_id=uuid4(),
            analysis_run_id=uuid4(),
            created_at=CREATED_AT,
            available_at=CREATED_AT - timedelta(seconds=1),
        )


def test_claims_available_pending_job() -> None:
    pending = enqueue_job()

    running = pending.claim(
        claimed_at=CLAIMED_AT,
    )

    assert running.status is AnalysisExecutionJobStatus.RUNNING
    assert running.attempt_count == 1
    assert running.claimed_at == CLAIMED_AT
    assert running.completed_at is None
    assert running.last_error is None

    assert pending.status is AnalysisExecutionJobStatus.PENDING
    assert pending.attempt_count == 0


def test_cannot_claim_job_before_available_time() -> None:
    pending = enqueue_job()

    with pytest.raises(
        InvalidAnalysisExecutionJobTransitionError,
        match=("Analysis execution job is not available for claiming"),
    ):
        pending.claim(
            claimed_at=(AVAILABLE_AT - timedelta(seconds=1)),
        )


def test_only_pending_job_can_be_claimed() -> None:
    running = running_job()

    with pytest.raises(
        InvalidAnalysisExecutionJobTransitionError,
        match="cannot be claimed",
    ):
        running.claim(
            claimed_at=(CLAIMED_AT + timedelta(seconds=1)),
        )


def test_marks_running_job_succeeded() -> None:
    running = running_job()

    succeeded = running.mark_succeeded(
        completed_at=COMPLETED_AT,
    )

    assert succeeded.status is AnalysisExecutionJobStatus.SUCCEEDED
    assert succeeded.completed_at == COMPLETED_AT
    assert succeeded.claimed_at == CLAIMED_AT
    assert succeeded.last_error is None


def test_retries_running_job_when_attempts_remain() -> None:
    running = running_job(
        max_attempts=3,
    )

    retry_at = COMPLETED_AT + timedelta(minutes=1)

    pending = running.retry(
        failed_at=COMPLETED_AT,
        available_at=retry_at,
        error="Estimator dependency temporarily unavailable.",
    )

    assert pending.status is AnalysisExecutionJobStatus.PENDING
    assert pending.attempt_count == 1
    assert pending.available_at == retry_at
    assert pending.claimed_at is None
    assert pending.completed_at is None
    assert pending.last_error == ("Estimator dependency temporarily unavailable.")


def test_retry_rejects_exhausted_job() -> None:
    running = running_job(
        max_attempts=1,
    )

    with pytest.raises(
        InvalidAnalysisExecutionJobTransitionError,
        match="has exhausted its attempts",
    ):
        running.retry(
            failed_at=COMPLETED_AT,
            available_at=(COMPLETED_AT + timedelta(minutes=1)),
            error="Estimator dependency unavailable.",
        )


def test_marks_running_job_dead_letter() -> None:
    running = running_job(
        max_attempts=1,
    )

    dead_letter = running.mark_dead_letter(
        completed_at=COMPLETED_AT,
        error="Estimator dependency remained unavailable.",
    )

    assert dead_letter.status is AnalysisExecutionJobStatus.DEAD_LETTER
    assert dead_letter.completed_at == COMPLETED_AT
    assert dead_letter.last_error == ("Estimator dependency remained unavailable.")


def test_job_error_must_not_be_blank() -> None:
    running = running_job()

    with pytest.raises(
        InvalidAnalysisExecutionJobTransitionError,
        match=("Analysis execution job error must not be blank"),
    ):
        running.retry(
            failed_at=COMPLETED_AT,
            available_at=(COMPLETED_AT + timedelta(minutes=1)),
            error="   ",
        )


def test_completion_cannot_precede_claim() -> None:
    running = running_job()

    with pytest.raises(
        InvalidAnalysisExecutionJobTransitionError,
        match=("Analysis execution completion timestamp cannot precede its claim timestamp"),
    ):
        running.mark_succeeded(
            completed_at=(CLAIMED_AT - timedelta(seconds=1)),
        )


def test_retry_availability_cannot_precede_failure() -> None:
    running = running_job()

    with pytest.raises(
        InvalidAnalysisExecutionJobTransitionError,
        match=("Analysis execution retry availability cannot precede failure"),
    ):
        running.retry(
            failed_at=FAILED_AT,
            available_at=(FAILED_AT - timedelta(seconds=1)),
            error="Estimator dependency unavailable.",
        )


def test_transition_timestamps_must_be_timezone_aware() -> None:
    running = running_job()

    with pytest.raises(
        InvalidAnalysisExecutionJobTransitionError,
        match=("Analysis execution job timestamps must be timezone-aware"),
    ):
        running.mark_succeeded(
            completed_at=datetime(
                2026,
                7,
                16,
                10,
                4,
            ),
        )
