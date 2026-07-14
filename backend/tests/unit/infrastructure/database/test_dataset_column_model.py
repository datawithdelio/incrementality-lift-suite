from sqlalchemy import (
    CheckConstraint,
    Index,
    UniqueConstraint,
)

from incrementality_api.infrastructure.database import (
    models as database_models,
)


def test_dataset_column_table_contract() -> None:
    model = getattr(
        database_models,
        "DatasetColumnModel",
        None,
    )

    assert model is not None

    table = model.__table__

    assert table.name == "dataset_columns"

    assert set(table.columns.keys()) == {
        "id",
        "dataset_id",
        "ordinal_position",
        "source_name",
        "normalized_name",
        "inferred_type",
        "nullable",
        "missing_count",
        "created_at",
        "updated_at",
    }

    assert table.c.source_name.type.length == 255
    assert table.c.normalized_name.type.length == 255
    assert table.c.inferred_type.type.length == 32

    foreign_keys = list(table.c.dataset_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "datasets.id"
    assert foreign_keys[0].ondelete == "CASCADE"

    unique_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    }

    assert "uq_dataset_columns_dataset_ordinal" in unique_constraint_names
    assert "uq_dataset_columns_dataset_normalized_name" in unique_constraint_names

    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(
            constraint,
            CheckConstraint,
        )
    }

    assert "ck_dataset_columns_ordinal_positive" in check_constraints
    assert "ck_dataset_columns_source_name_not_blank" in check_constraints
    assert "ck_dataset_columns_normalized_name_not_blank" in check_constraints
    assert "ck_dataset_columns_inferred_type" in check_constraints
    assert "ck_dataset_columns_missing_nonnegative" in check_constraints
    assert "ck_dataset_columns_nullable_consistency" in check_constraints

    inferred_type_expression = check_constraints["ck_dataset_columns_inferred_type"]

    for inferred_type in (
        "boolean",
        "integer",
        "float",
        "date",
        "datetime",
        "string",
    ):
        assert inferred_type in (inferred_type_expression)

    index_names = {index.name for index in table.indexes if isinstance(index, Index)}

    assert "ix_dataset_columns_dataset_id" in index_names
