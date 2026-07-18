from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import Uuid

from incrementality_api.infrastructure.database.models.analysis_runs import (
    AnalysisRunModel,
)
from incrementality_api.infrastructure.database.models.dataset_semantic_mappings import (
    DatasetSemanticMappingModel,
)
from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
)


def constraint_names(
    model: type[AnalysisRunModel | DatasetModel | DatasetSemanticMappingModel],
) -> set[str]:
    return {
        constraint.name for constraint in model.__table__.constraints if constraint.name is not None
    }


def index_names(
    model: type[AnalysisRunModel],
) -> set[str]:
    return {index.name for index in model.__table__.indexes if index.name is not None}


def test_analysis_run_table_and_columns() -> None:
    table = AnalysisRunModel.__table__

    assert table.name == "analysis_runs"

    assert set(table.columns.keys()) == {
        "id",
        "workspace_id",
        "project_id",
        "dataset_id",
        "dataset_checksum_sha256",
        "dataset_byte_size",
        "semantic_mapping_id",
        "semantic_mapping_version",
        "created_by_user_id",
        "estimator_type",
        "estimator_version",
        "application_version",
        "source_revision",
        "statistical_library_versions_json",
        "semantic_mapping_snapshot_json",
        "analysis_period_snapshot_json",
        "analysis_selection_snapshot_json",
        "treatment_control_snapshot_json",
        "estimand_snapshot_json",
        "random_seed",
        "input_fingerprint_sha256",
        "configuration_json",
        "status",
        "started_at",
        "completed_at",
        "failure_reason",
        "cancellation_reason",
        "created_at",
        "updated_at",
    }

    assert isinstance(
        table.c.id.type,
        Uuid,
    )
    assert table.c.id.primary_key

    for column_name in (
        "workspace_id",
        "project_id",
        "dataset_id",
        "semantic_mapping_id",
        "created_by_user_id",
    ):
        column = table.c[column_name]

        assert isinstance(
            column.type,
            Uuid,
        )
        assert not column.nullable

    assert isinstance(
        table.c.dataset_checksum_sha256.type,
        String,
    )
    assert table.c.dataset_checksum_sha256.type.length == 64
    assert not table.c.dataset_checksum_sha256.nullable

    assert isinstance(
        table.c.dataset_byte_size.type,
        Integer,
    )
    assert not table.c.dataset_byte_size.nullable

    assert isinstance(
        table.c.semantic_mapping_version.type,
        Integer,
    )
    assert not table.c.semantic_mapping_version.nullable

    assert isinstance(
        table.c.estimator_type.type,
        String,
    )
    assert table.c.estimator_type.type.length == 64
    assert not table.c.estimator_type.nullable

    assert isinstance(
        table.c.estimator_version.type,
        String,
    )
    assert table.c.estimator_version.type.length == 255
    assert not table.c.estimator_version.nullable

    assert isinstance(
        table.c.application_version.type,
        String,
    )
    assert table.c.application_version.type.length == 255
    assert table.c.application_version.nullable

    assert isinstance(
        table.c.source_revision.type,
        String,
    )
    assert table.c.source_revision.type.length == 255
    assert table.c.source_revision.nullable

    assert isinstance(
        table.c.statistical_library_versions_json.type,
        Text,
    )
    assert table.c.statistical_library_versions_json.nullable

    assert isinstance(
        table.c.semantic_mapping_snapshot_json.type,
        Text,
    )
    assert table.c.semantic_mapping_snapshot_json.nullable

    assert isinstance(table.c.analysis_period_snapshot_json.type, Text)
    assert table.c.analysis_period_snapshot_json.nullable

    assert isinstance(table.c.analysis_selection_snapshot_json.type, Text)
    assert table.c.analysis_selection_snapshot_json.nullable

    assert isinstance(table.c.treatment_control_snapshot_json.type, Text)
    assert table.c.treatment_control_snapshot_json.nullable

    assert isinstance(table.c.estimand_snapshot_json.type, Text)
    assert table.c.estimand_snapshot_json.nullable

    assert isinstance(
        table.c.random_seed.type,
        BigInteger,
    )
    assert table.c.random_seed.nullable

    assert isinstance(
        table.c.input_fingerprint_sha256.type,
        String,
    )
    assert table.c.input_fingerprint_sha256.type.length == 64
    assert table.c.input_fingerprint_sha256.nullable

    assert isinstance(
        table.c.configuration_json.type,
        Text,
    )
    assert not table.c.configuration_json.nullable

    assert isinstance(
        table.c.status.type,
        String,
    )
    assert table.c.status.type.length == 32
    assert not table.c.status.nullable

    for column_name in (
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    ):
        column = table.c[column_name]

        assert isinstance(
            column.type,
            DateTime,
        )
        assert column.type.timezone is True

    assert table.c.started_at.nullable
    assert table.c.completed_at.nullable
    assert not table.c.created_at.nullable
    assert not table.c.updated_at.nullable

    for column_name in (
        "failure_reason",
        "cancellation_reason",
    ):
        column = table.c[column_name]

        assert isinstance(
            column.type,
            String,
        )
        assert column.type.length == 2_000
        assert column.nullable


def test_analysis_run_has_named_integrity_constraints() -> None:
    assert constraint_names(AnalysisRunModel).issuperset(
        {
            "ck_analysis_runs_mapping_version_positive",
            "ck_analysis_runs_dataset_checksum_sha256_format",
            "ck_analysis_runs_dataset_byte_size_positive",
            "ck_analysis_runs_input_fingerprint_sha256_format",
            "ck_analysis_runs_estimator_type",
            "ck_analysis_runs_estimator_version_not_blank",
            "ck_analysis_runs_application_version_not_blank",
            "ck_analysis_runs_source_revision_not_blank",
            "ck_analysis_runs_statistical_library_versions_not_blank",
            "ck_analysis_runs_statistical_library_versions_object",
            "ck_analysis_runs_statistical_library_versions_not_empty",
            "ck_analysis_runs_treatment_control_snapshot_not_blank",
            "ck_analysis_runs_treatment_control_snapshot_object",
            "ck_analysis_runs_treatment_control_snapshot_not_empty",
            "ck_analysis_runs_mapping_snapshot_not_blank",
            "ck_analysis_runs_mapping_snapshot_object",
            "ck_analysis_runs_period_snapshot_not_blank",
            "ck_analysis_runs_period_snapshot_object",
            "ck_analysis_runs_period_snapshot_not_empty",
            "ck_analysis_runs_selection_snapshot_not_blank",
            "ck_analysis_runs_selection_snapshot_object",
            "ck_analysis_runs_selection_snapshot_not_empty",
            "ck_analysis_runs_configuration_not_blank",
            "ck_analysis_runs_configuration_object",
            "ck_analysis_runs_status",
            "ck_analysis_runs_failure_reason_not_blank",
            "ck_analysis_runs_cancellation_reason_not_blank",
            "ck_analysis_runs_start_after_create",
            "ck_analysis_runs_completion_after_start",
            "ck_analysis_runs_lifecycle_metadata",
            "fk_analysis_runs_dataset_scope",
            "fk_analysis_runs_semantic_mapping_snapshot",
            "fk_analysis_runs_creator",
        }
    )


def test_analysis_run_enforces_exact_dataset_scope() -> None:
    foreign_key = next(
        constraint
        for constraint in (AnalysisRunModel.__table__.constraints)
        if (
            isinstance(
                constraint,
                ForeignKeyConstraint,
            )
            and constraint.name == "fk_analysis_runs_dataset_scope"
        )
    )

    assert tuple(foreign_key.column_keys) == (
        "dataset_id",
        "workspace_id",
        "project_id",
    )

    assert tuple(element.target_fullname for element in foreign_key.elements) == (
        "datasets.id",
        "datasets.workspace_id",
        "datasets.project_id",
    )

    assert foreign_key.ondelete == "CASCADE"


def test_analysis_run_enforces_exact_mapping_snapshot() -> None:
    foreign_key = next(
        constraint
        for constraint in (AnalysisRunModel.__table__.constraints)
        if (
            isinstance(
                constraint,
                ForeignKeyConstraint,
            )
            and constraint.name == ("fk_analysis_runs_semantic_mapping_snapshot")
        )
    )

    assert tuple(foreign_key.column_keys) == (
        "semantic_mapping_id",
        "dataset_id",
        "semantic_mapping_version",
    )

    assert tuple(element.target_fullname for element in foreign_key.elements) == (
        "dataset_semantic_mappings.id",
        "dataset_semantic_mappings.dataset_id",
        "dataset_semantic_mappings.version",
    )

    assert foreign_key.deferrable is True
    assert foreign_key.initially == "DEFERRED"


def test_parent_tables_expose_composite_candidate_keys() -> None:
    dataset_unique_constraints = {
        constraint.name
        for constraint in (DatasetModel.__table__.constraints)
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    }

    mapping_unique_constraints = {
        constraint.name
        for constraint in (DatasetSemanticMappingModel.__table__.constraints)
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    }

    assert "uq_datasets_id_workspace_project" in dataset_unique_constraints

    assert "uq_dataset_semantic_mappings_id_dataset_version" in mapping_unique_constraints


def test_analysis_run_has_query_indexes() -> None:
    assert index_names(AnalysisRunModel) == {
        ("ix_analysis_runs_workspace_project_created_at"),
        "ix_analysis_runs_dataset_created_at",
        "ix_analysis_runs_status_created_at",
        "ix_analysis_runs_semantic_mapping_id",
        "ix_analysis_runs_created_by_user_id",
    }


def test_analysis_run_estimand_snapshot_has_json_constraints() -> None:
    names = constraint_names(AnalysisRunModel)

    assert "ck_analysis_runs_estimand_snapshot_not_blank" in names
    assert "ck_analysis_runs_estimand_snapshot_object" in names
    assert "ck_analysis_runs_estimand_snapshot_not_empty" in names
