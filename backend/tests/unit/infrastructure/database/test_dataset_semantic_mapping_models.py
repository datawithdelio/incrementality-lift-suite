from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Table,
    UniqueConstraint,
)

from incrementality_api.infrastructure.database import (
    models as database_models,
)
from incrementality_api.infrastructure.database.base import Base

del database_models


def get_table(name: str) -> Table:
    assert name in Base.metadata.tables, f"Table {name!r} is not registered."

    return Base.metadata.tables[name]


def unique_constraint_names(
    table: Table,
) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(
            constraint,
            UniqueConstraint,
        )
        and constraint.name is not None
    }


def check_constraint_names(
    table: Table,
) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(
            constraint,
            CheckConstraint,
        )
        and constraint.name is not None
    }


def foreign_key_constraints(
    table: Table,
) -> dict[str, ForeignKeyConstraint]:
    return {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(
            constraint,
            ForeignKeyConstraint,
        )
        and constraint.name is not None
    }


def local_columns(
    constraint: ForeignKeyConstraint,
) -> tuple[str, ...]:
    return tuple(element.parent.name for element in constraint.elements)


def remote_columns(
    constraint: ForeignKeyConstraint,
) -> tuple[str, ...]:
    return tuple(element.target_fullname for element in constraint.elements)


def test_semantic_mapping_tables_are_registered() -> None:
    assert {
        "dataset_semantic_mappings",
        "dataset_mapping_covariates",
    }.issubset(
        Base.metadata.tables,
    )


def test_dataset_semantic_mapping_table_contract() -> None:
    table = get_table(
        "dataset_semantic_mappings",
    )

    assert set(table.columns.keys()) == {
        "id",
        "dataset_id",
        "created_by_user_id",
        "version",
        "time_column",
        "unit_column",
        "treatment_column",
        "outcome_column",
        "spend_column",
        "treatment_value",
        "control_value",
        "created_at",
        "updated_at",
    }

    assert table.primary_key.columns.keys() == [
        "id",
    ]

    assert table.c.time_column.type.length == 255
    assert table.c.unit_column.type.length == 255
    assert table.c.treatment_column.type.length == 255
    assert table.c.outcome_column.type.length == 255
    assert table.c.spend_column.type.length == 255
    assert table.c.treatment_value.type.length == 255
    assert table.c.control_value.type.length == 255

    for optional_column in (
        "spend_column",
        "treatment_column",
        "treatment_value",
        "control_value",
    ):
        assert table.c[optional_column].nullable is True

    for required_column in (
        "dataset_id",
        "created_by_user_id",
        "version",
        "time_column",
        "unit_column",
        "outcome_column",
    ):
        assert table.c[required_column].nullable is False


def test_semantic_mapping_uniqueness_contract() -> None:
    table = get_table(
        "dataset_semantic_mappings",
    )

    names = unique_constraint_names(table)

    assert "uq_dataset_semantic_mappings_dataset_version" in names
    assert "uq_dataset_semantic_mappings_id_dataset" in names


def test_semantic_mapping_foreign_keys_are_scoped() -> None:
    table = get_table(
        "dataset_semantic_mappings",
    )
    constraints = foreign_key_constraints(table)

    dataset_constraint = constraints["fk_dataset_semantic_mappings_dataset"]

    assert local_columns(dataset_constraint) == ("dataset_id",)
    assert remote_columns(dataset_constraint) == ("datasets.id",)
    assert dataset_constraint.ondelete == "CASCADE"

    creator_constraint = constraints["fk_dataset_semantic_mappings_creator"]

    assert local_columns(creator_constraint) == ("created_by_user_id",)
    assert remote_columns(creator_constraint) == ("users.id",)
    assert creator_constraint.ondelete == "RESTRICT"

    expected_role_constraints = {
        "fk_dataset_semantic_mappings_time_column": ("time_column",),
        "fk_dataset_semantic_mappings_unit_column": ("unit_column",),
        "fk_dataset_semantic_mappings_treatment_column": ("treatment_column",),
        "fk_dataset_semantic_mappings_outcome_column": ("outcome_column",),
        "fk_dataset_semantic_mappings_spend_column": ("spend_column",),
    }

    for (
        constraint_name,
        role_column,
    ) in expected_role_constraints.items():
        constraint = constraints[constraint_name]

        assert local_columns(constraint) == (
            "dataset_id",
            *role_column,
        )
        assert remote_columns(constraint) == (
            "dataset_columns.dataset_id",
            ("dataset_columns.normalized_name"),
        )


def test_semantic_mapping_checks_exist() -> None:
    table = get_table(
        "dataset_semantic_mappings",
    )
    names = check_constraint_names(table)

    expected = {
        "ck_dataset_semantic_mappings_version_positive",
        "ck_dataset_semantic_mappings_time_not_blank",
        "ck_dataset_semantic_mappings_unit_not_blank",
        "ck_dataset_semantic_mappings_treatment_not_blank",
        "ck_dataset_semantic_mappings_outcome_not_blank",
        "ck_dataset_semantic_mappings_spend_not_blank",
        "ck_dataset_semantic_mappings_treatment_value_not_blank",
        "ck_dataset_semantic_mappings_control_value_not_blank",
        "ck_dataset_semantic_mappings_roles_distinct",
        "ck_dataset_semantic_mappings_values_distinct",
    }

    assert expected.issubset(names)


def test_mapping_covariate_table_contract() -> None:
    table = get_table(
        "dataset_mapping_covariates",
    )

    assert set(table.columns.keys()) == {
        "id",
        "mapping_id",
        "dataset_id",
        "ordinal_position",
        "normalized_column_name",
        "created_at",
        "updated_at",
    }

    assert table.primary_key.columns.keys() == [
        "id",
    ]

    assert table.c.normalized_column_name.type.length == 255

    for required_column in (
        "mapping_id",
        "dataset_id",
        "ordinal_position",
        "normalized_column_name",
    ):
        assert table.c[required_column].nullable is False


def test_mapping_covariate_uniqueness_contract() -> None:
    table = get_table(
        "dataset_mapping_covariates",
    )
    names = unique_constraint_names(table)

    assert "uq_dataset_mapping_covariates_mapping_ordinal" in names
    assert "uq_dataset_mapping_covariates_mapping_column" in names


def test_mapping_covariate_foreign_keys_are_scoped() -> None:
    table = get_table(
        "dataset_mapping_covariates",
    )
    constraints = foreign_key_constraints(table)

    mapping_constraint = constraints["fk_dataset_mapping_covariates_mapping"]

    assert local_columns(mapping_constraint) == (
        "mapping_id",
        "dataset_id",
    )
    assert remote_columns(mapping_constraint) == (
        "dataset_semantic_mappings.id",
        "dataset_semantic_mappings.dataset_id",
    )
    assert mapping_constraint.ondelete == "CASCADE"

    column_constraint = constraints["fk_dataset_mapping_covariates_column"]

    assert local_columns(column_constraint) == (
        "dataset_id",
        "normalized_column_name",
    )
    assert remote_columns(column_constraint) == (
        "dataset_columns.dataset_id",
        "dataset_columns.normalized_name",
    )


def test_mapping_covariate_checks_exist() -> None:
    table = get_table(
        "dataset_mapping_covariates",
    )
    names = check_constraint_names(table)

    assert {
        "ck_dataset_mapping_covariates_ordinal_positive",
        "ck_dataset_mapping_covariates_column_not_blank",
    }.issubset(names)
