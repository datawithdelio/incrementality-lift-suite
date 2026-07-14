from sqlalchemy import CheckConstraint

from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
)


def test_dataset_table_accepts_only_csv_media_type() -> None:
    constraint = next(
        constraint
        for constraint in DatasetModel.__table__.constraints
        if (
            isinstance(
                constraint,
                CheckConstraint,
            )
            and constraint.name == "ck_datasets_media_type"
        )
    )

    expression = str(constraint.sqltext)

    assert "text/csv" in expression
    assert "application/vnd.apache.parquet" not in expression
