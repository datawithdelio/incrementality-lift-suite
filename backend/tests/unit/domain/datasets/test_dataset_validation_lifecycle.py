from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetTransitionError,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

UPLOADED_AT = datetime(
    2026,
    7,
    15,
    9,
    0,
    tzinfo=UTC,
)

VALIDATION_STARTED_AT = datetime(
    2026,
    7,
    15,
    9,
    5,
    tzinfo=UTC,
)

VALIDATION_COMPLETED_AT = datetime(
    2026,
    7,
    15,
    9,
    7,
    tzinfo=UTC,
)


def build_pending_dataset() -> Dataset:
    return Dataset.register(
        workspace_id=uuid4(),
        project_id=uuid4(),
        created_by_user_id=uuid4(),
        source_filename="campaign-results.csv",
        storage_key=(
            "workspaces/workspace-1/projects/project-1/datasets/checksum/campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=1_024,
        checksum_sha256="a" * 64,
    )


def build_uploaded_dataset() -> Dataset:
    return build_pending_dataset().mark_uploaded(
        uploaded_at=UPLOADED_AT,
    )


def build_validating_dataset() -> Dataset:
    return build_uploaded_dataset().begin_validation(
        validation_started_at=VALIDATION_STARTED_AT,
    )


def test_uploaded_dataset_can_begin_validation() -> None:
    uploaded = build_uploaded_dataset()

    validating = uploaded.begin_validation(
        validation_started_at=VALIDATION_STARTED_AT,
    )

    assert validating.status is DatasetStatus.VALIDATING
    assert validating.validation_started_at == VALIDATION_STARTED_AT
    assert validating.validation_completed_at is None
    assert validating.row_count is None
    assert validating.column_count is None
    assert validating.failure_reason is None

    assert uploaded.status is DatasetStatus.UPLOADED
    assert uploaded.validation_started_at is None


def test_only_uploaded_dataset_can_begin_validation() -> None:
    pending = build_pending_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match=("Dataset in status 'pending_upload' cannot begin validation"),
    ):
        pending.begin_validation(
            validation_started_at=VALIDATION_STARTED_AT,
        )


def test_validation_start_timestamp_must_be_aware() -> None:
    uploaded = build_uploaded_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match=("Validation start timestamp must be timezone-aware"),
    ):
        uploaded.begin_validation(
            validation_started_at=datetime(
                2026,
                7,
                15,
                9,
                5,
            ),
        )


def test_validating_dataset_can_be_marked_ready() -> None:
    validating = build_validating_dataset()

    ready = validating.mark_ready(
        validation_completed_at=VALIDATION_COMPLETED_AT,
        row_count=250,
        column_count=8,
    )

    assert ready.status is DatasetStatus.READY
    assert ready.validation_started_at == VALIDATION_STARTED_AT
    assert ready.validation_completed_at == VALIDATION_COMPLETED_AT
    assert ready.row_count == 250
    assert ready.column_count == 8
    assert ready.failure_reason is None

    assert validating.status is DatasetStatus.VALIDATING
    assert validating.validation_completed_at is None


def test_only_validating_dataset_can_be_marked_ready() -> None:
    uploaded = build_uploaded_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match=("Dataset in status 'uploaded' cannot be marked ready"),
    ):
        uploaded.mark_ready(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            row_count=250,
            column_count=8,
        )


def test_ready_completion_timestamp_must_be_aware() -> None:
    validating = build_validating_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match=("Validation completion timestamp must be timezone-aware"),
    ):
        validating.mark_ready(
            validation_completed_at=datetime(
                2026,
                7,
                15,
                9,
                7,
            ),
            row_count=250,
            column_count=8,
        )


def test_ready_completion_cannot_precede_start() -> None:
    validating = build_validating_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match=("Validation completion timestamp cannot precede the validation start timestamp"),
    ):
        validating.mark_ready(
            validation_completed_at=(VALIDATION_STARTED_AT - timedelta(seconds=1)),
            row_count=250,
            column_count=8,
        )


def test_ready_row_count_must_be_nonnegative() -> None:
    validating = build_validating_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match="Row count must be nonnegative",
    ):
        validating.mark_ready(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            row_count=-1,
            column_count=8,
        )


def test_ready_column_count_must_be_positive() -> None:
    validating = build_validating_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match="Column count must be positive",
    ):
        validating.mark_ready(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            row_count=250,
            column_count=0,
        )


def test_validating_dataset_can_be_marked_failed() -> None:
    validating = build_validating_dataset()

    failed = validating.mark_failed(
        validation_completed_at=VALIDATION_COMPLETED_AT,
        failure_reason=("CSV contains duplicate column names."),
    )

    assert failed.status is DatasetStatus.FAILED
    assert failed.validation_started_at == VALIDATION_STARTED_AT
    assert failed.validation_completed_at == VALIDATION_COMPLETED_AT
    assert failed.row_count is None
    assert failed.column_count is None
    assert failed.failure_reason == ("CSV contains duplicate column names.")

    assert validating.status is DatasetStatus.VALIDATING
    assert validating.failure_reason is None


def test_only_validating_dataset_can_be_marked_failed() -> None:
    uploaded = build_uploaded_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match=("Dataset in status 'uploaded' cannot be marked failed"),
    ):
        uploaded.mark_failed(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            failure_reason="Malformed CSV.",
        )


def test_failed_completion_timestamp_must_be_aware() -> None:
    validating = build_validating_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match=("Validation completion timestamp must be timezone-aware"),
    ):
        validating.mark_failed(
            validation_completed_at=datetime(
                2026,
                7,
                15,
                9,
                7,
            ),
            failure_reason="Malformed CSV.",
        )


def test_failed_completion_cannot_precede_start() -> None:
    validating = build_validating_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match=("Validation completion timestamp cannot precede the validation start timestamp"),
    ):
        validating.mark_failed(
            validation_completed_at=(VALIDATION_STARTED_AT - timedelta(seconds=1)),
            failure_reason="Malformed CSV.",
        )


def test_failure_reason_must_not_be_blank() -> None:
    validating = build_validating_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match="Failure reason must not be blank",
    ):
        validating.mark_failed(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            failure_reason="   ",
        )


def test_failure_reason_must_fit_persistence_limit() -> None:
    validating = build_validating_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match=("Failure reason must not exceed 2000 characters"),
    ):
        validating.mark_failed(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            failure_reason="x" * 2_001,
        )
