from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetTransitionError,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

CHECKSUM = "a" * 64

UPLOADED_AT = datetime(
    2026,
    7,
    14,
    12,
    30,
    tzinfo=UTC,
)


def build_pending_dataset() -> Dataset:
    workspace_id = uuid4()
    project_id = uuid4()

    return Dataset.register(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=uuid4(),
        source_filename="campaign-results.csv",
        storage_key=(
            f"workspaces/{workspace_id}/"
            f"projects/{project_id}/"
            f"datasets/{CHECKSUM}/"
            "campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=4096,
        checksum_sha256=CHECKSUM,
    )


def test_marks_pending_dataset_as_uploaded() -> None:
    original = build_pending_dataset()

    uploaded = original.mark_uploaded(
        uploaded_at=UPLOADED_AT,
    )

    assert uploaded is not original
    assert uploaded.id == original.id
    assert uploaded.status is DatasetStatus.UPLOADED
    assert uploaded.uploaded_at == UPLOADED_AT

    assert uploaded.validation_completed_at is None
    assert uploaded.row_count is None
    assert uploaded.column_count is None
    assert uploaded.failure_reason is None

    assert original.status is DatasetStatus.PENDING_UPLOAD
    assert original.uploaded_at is None


def test_rejects_repeated_uploaded_transition() -> None:
    dataset = build_pending_dataset().mark_uploaded(
        uploaded_at=UPLOADED_AT,
    )

    with pytest.raises(
        InvalidDatasetTransitionError,
        match="cannot be marked uploaded",
    ):
        dataset.mark_uploaded(
            uploaded_at=UPLOADED_AT,
        )


def test_rejects_uploaded_transition_from_other_status() -> None:
    dataset = replace(
        build_pending_dataset(),
        status=DatasetStatus.VALIDATING,
    )

    with pytest.raises(
        InvalidDatasetTransitionError,
        match="cannot be marked uploaded",
    ):
        dataset.mark_uploaded(
            uploaded_at=UPLOADED_AT,
        )


def test_rejects_naive_upload_timestamp() -> None:
    dataset = build_pending_dataset()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match="Upload timestamp",
    ):
        dataset.mark_uploaded(
            uploaded_at=datetime(
                2026,
                7,
                14,
                12,
                30,
            ),
        )
