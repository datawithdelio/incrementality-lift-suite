from datetime import UTC, datetime
from uuid import uuid4

from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.infrastructure.database.repositories.datasets import (
    to_dataset_entity,
    to_dataset_model,
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


def build_uploaded_dataset() -> Dataset:
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
    ).mark_uploaded(
        uploaded_at=UPLOADED_AT,
    )


def round_trip(dataset: Dataset) -> Dataset:
    model = to_dataset_model(dataset)

    assert model.validation_started_at == (dataset.validation_started_at)

    return to_dataset_entity(model)


def test_round_trips_validating_dataset_metadata() -> None:
    dataset = build_uploaded_dataset().begin_validation(
        validation_started_at=VALIDATION_STARTED_AT,
    )

    result = round_trip(dataset)

    assert result == dataset
    assert result.validation_started_at == VALIDATION_STARTED_AT
    assert result.validation_completed_at is None
    assert result.row_count is None
    assert result.column_count is None
    assert result.failure_reason is None


def test_round_trips_ready_dataset_metadata() -> None:
    dataset = (
        build_uploaded_dataset()
        .begin_validation(
            validation_started_at=(VALIDATION_STARTED_AT),
        )
        .mark_ready(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            row_count=250,
            column_count=8,
        )
    )

    result = round_trip(dataset)

    assert result == dataset
    assert result.validation_started_at == VALIDATION_STARTED_AT
    assert result.validation_completed_at == VALIDATION_COMPLETED_AT
    assert result.row_count == 250
    assert result.column_count == 8
    assert result.failure_reason is None


def test_round_trips_failed_dataset_metadata() -> None:
    dataset = (
        build_uploaded_dataset()
        .begin_validation(
            validation_started_at=(VALIDATION_STARTED_AT),
        )
        .mark_failed(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            failure_reason=("CSV contains duplicate column names."),
        )
    )

    result = round_trip(dataset)

    assert result == dataset
    assert result.validation_started_at == VALIDATION_STARTED_AT
    assert result.validation_completed_at == VALIDATION_COMPLETED_AT
    assert result.row_count is None
    assert result.column_count is None
    assert result.failure_reason == ("CSV contains duplicate column names.")
