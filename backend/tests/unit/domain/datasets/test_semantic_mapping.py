from datetime import UTC, datetime
from uuid import uuid4

import pytest

from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetSemanticMappingError,
)
from incrementality_api.domain.datasets.semantic_mapping import (
    DatasetSemanticMapping,
)

UPLOADED_AT = datetime(
    2026,
    7,
    14,
    20,
    0,
    tzinfo=UTC,
)

VALIDATION_STARTED_AT = datetime(
    2026,
    7,
    14,
    20,
    5,
    tzinfo=UTC,
)

VALIDATION_COMPLETED_AT = datetime(
    2026,
    7,
    14,
    20,
    10,
    tzinfo=UTC,
)

MAPPING_CREATED_AT = datetime(
    2026,
    7,
    14,
    20,
    15,
    tzinfo=UTC,
)


def build_ready_dataset() -> Dataset:
    return (
        Dataset.register(
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
        .mark_uploaded(
            uploaded_at=UPLOADED_AT,
        )
        .begin_validation(
            validation_started_at=VALIDATION_STARTED_AT,
        )
        .mark_ready(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            row_count=100,
            column_count=6,
        )
    )


def build_columns() -> tuple[
    DatasetColumnProfile,
    ...,
]:
    return (
        DatasetColumnProfile(
            ordinal_position=1,
            source_name="Date",
            normalized_name="date",
            inferred_type=DatasetColumnType.DATE,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=2,
            source_name="Market",
            normalized_name="market",
            inferred_type=DatasetColumnType.STRING,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=3,
            source_name="Treated",
            normalized_name="treated",
            inferred_type=DatasetColumnType.BOOLEAN,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=4,
            source_name="Revenue",
            normalized_name="revenue",
            inferred_type=DatasetColumnType.FLOAT,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=5,
            source_name="Spend",
            normalized_name="spend",
            inferred_type=DatasetColumnType.INTEGER,
            nullable=True,
            missing_count=2,
        ),
        DatasetColumnProfile(
            ordinal_position=6,
            source_name="Promotion",
            normalized_name="promotion",
            inferred_type=DatasetColumnType.STRING,
            nullable=False,
            missing_count=0,
        ),
    )


def create_mapping(
    **overrides: object,
) -> DatasetSemanticMapping:
    arguments: dict[str, object] = {
        "dataset": build_ready_dataset(),
        "columns": build_columns(),
        "created_by_user_id": uuid4(),
        "version": 1,
        "time_column": "Date",
        "unit_column": "Market",
        "treatment_column": "Treated",
        "outcome_column": "Revenue",
        "spend_column": "Spend",
        "covariate_columns": ("Promotion",),
        "treatment_value": " true ",
        "control_value": " false ",
        "created_at": MAPPING_CREATED_AT,
    }

    arguments.update(overrides)

    return DatasetSemanticMapping.create(
        **arguments,
    )


def test_creates_valid_semantic_mapping() -> None:
    dataset = build_ready_dataset()
    created_by_user_id = uuid4()

    mapping = DatasetSemanticMapping.create(
        dataset=dataset,
        columns=build_columns(),
        created_by_user_id=created_by_user_id,
        version=1,
        time_column="Date",
        unit_column="Market",
        treatment_column="Treated",
        outcome_column="Revenue",
        spend_column="Spend",
        covariate_columns=("Promotion",),
        treatment_value=" true ",
        control_value=" false ",
        created_at=MAPPING_CREATED_AT,
    )

    assert mapping.dataset_id == dataset.id
    assert mapping.created_by_user_id == (created_by_user_id)
    assert mapping.version == 1
    assert mapping.time_column == "date"
    assert mapping.unit_column == "market"
    assert mapping.treatment_column == "treated"
    assert mapping.outcome_column == "revenue"
    assert mapping.spend_column == "spend"
    assert mapping.covariate_columns == ("promotion",)
    assert mapping.treatment_value == "true"
    assert mapping.control_value == "false"
    assert mapping.created_at == MAPPING_CREATED_AT
    assert mapping.updated_at == MAPPING_CREATED_AT


def test_creates_mmm_mapping_without_treatment_roles() -> None:
    mapping = create_mapping(
        treatment_column=None,
        treatment_value=None,
        control_value=None,
    )

    assert mapping.treatment_column is None
    assert mapping.treatment_value is None
    assert mapping.control_value is None


def test_rejects_partial_treatment_mapping() -> None:
    with pytest.raises(
        InvalidDatasetSemanticMappingError,
        match="must be supplied together",
    ):
        create_mapping(
            treatment_column=None,
        )


def test_rejects_dataset_that_is_not_ready() -> None:
    dataset = Dataset.register(
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

    with pytest.raises(
        InvalidDatasetSemanticMappingError,
        match="Dataset must be ready",
    ):
        create_mapping(
            dataset=dataset,
        )


def test_rejects_unknown_mapped_column() -> None:
    with pytest.raises(
        InvalidDatasetSemanticMappingError,
        match="does not exist",
    ):
        create_mapping(
            outcome_column="missing_revenue",
        )


def test_rejects_non_temporal_time_column() -> None:
    with pytest.raises(
        InvalidDatasetSemanticMappingError,
        match="Time column must be date or datetime",
    ):
        create_mapping(
            time_column="market",
            unit_column="date",
        )


def test_rejects_non_numeric_outcome_column() -> None:
    with pytest.raises(
        InvalidDatasetSemanticMappingError,
        match="Outcome column must be numeric",
    ):
        create_mapping(
            outcome_column="promotion",
            covariate_columns=("revenue",),
        )


def test_rejects_unsupported_treatment_type() -> None:
    with pytest.raises(
        InvalidDatasetSemanticMappingError,
        match=("Treatment column must be boolean, integer, or string"),
    ):
        create_mapping(
            treatment_column="revenue",
            outcome_column="spend",
            spend_column=None,
        )


def test_rejects_duplicate_semantic_roles() -> None:
    with pytest.raises(
        InvalidDatasetSemanticMappingError,
        match="Semantic roles must use distinct columns",
    ):
        create_mapping(
            outcome_column="treated",
        )


def test_rejects_covariate_role_overlap() -> None:
    with pytest.raises(
        InvalidDatasetSemanticMappingError,
        match=("Covariate columns must not overlap assigned semantic roles"),
    ):
        create_mapping(
            covariate_columns=("revenue",),
        )


def test_rejects_equal_treatment_and_control_values() -> None:
    with pytest.raises(
        InvalidDatasetSemanticMappingError,
        match=("Treatment and control values must be distinct"),
    ):
        create_mapping(
            treatment_value="TRUE",
            control_value="true",
        )
