"""Allow MMM semantic mappings without treatment roles.

Revision ID: f3b4c5d6e7a8
Revises: e7f8a9b0c1d2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3b4c5d6e7a8"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table = "dataset_semantic_mappings"

    op.drop_constraint(
        "ck_dataset_semantic_mappings_roles_distinct", table, type_="check"
    )
    op.drop_constraint(
        "ck_dataset_semantic_mappings_values_distinct", table, type_="check"
    )

    op.alter_column(table, "treatment_column", existing_type=sa.String(255), nullable=True)
    op.alter_column(table, "treatment_value", existing_type=sa.String(255), nullable=True)
    op.alter_column(table, "control_value", existing_type=sa.String(255), nullable=True)

    op.create_check_constraint(
        "ck_dataset_semantic_mappings_treatment_not_blank",
        table,
        "treatment_column IS NULL OR btrim(treatment_column) <> ''",
    )
    op.create_check_constraint(
        "ck_dataset_semantic_mappings_treatment_value_not_blank",
        table,
        "treatment_value IS NULL OR btrim(treatment_value) <> ''",
    )
    op.create_check_constraint(
        "ck_dataset_semantic_mappings_control_value_not_blank",
        table,
        "control_value IS NULL OR btrim(control_value) <> ''",
    )
    op.create_check_constraint(
        "ck_dataset_semantic_mappings_roles_distinct",
        table,
        """
        time_column <> unit_column
        AND time_column <> outcome_column
        AND unit_column <> outcome_column
        AND (treatment_column IS NULL OR (
            time_column <> treatment_column
            AND unit_column <> treatment_column
            AND treatment_column <> outcome_column
        ))
        AND (spend_column IS NULL OR (
            spend_column <> time_column
            AND spend_column <> unit_column
            AND (treatment_column IS NULL OR spend_column <> treatment_column)
            AND spend_column <> outcome_column
        ))
        """,
    )
    op.create_check_constraint(
        "ck_dataset_semantic_mappings_values_distinct",
        table,
        """
        (treatment_column IS NULL AND treatment_value IS NULL AND control_value IS NULL)
        OR (treatment_column IS NOT NULL AND treatment_value IS NOT NULL
            AND control_value IS NOT NULL
            AND lower(btrim(treatment_value)) <> lower(btrim(control_value)))
        """,
    )


def downgrade() -> None:
    table = "dataset_semantic_mappings"

    op.drop_constraint(
        "ck_dataset_semantic_mappings_treatment_not_blank", table, type_="check"
    )
    op.drop_constraint(
        "ck_dataset_semantic_mappings_treatment_value_not_blank", table, type_="check"
    )
    op.drop_constraint(
        "ck_dataset_semantic_mappings_control_value_not_blank", table, type_="check"
    )
    op.drop_constraint(
        "ck_dataset_semantic_mappings_roles_distinct", table, type_="check"
    )
    op.drop_constraint(
        "ck_dataset_semantic_mappings_values_distinct", table, type_="check"
    )

    missing_treatment_count = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM dataset_semantic_mappings "
            "WHERE treatment_column IS NULL OR treatment_value IS NULL OR control_value IS NULL"
        )
    )
    if missing_treatment_count:
        raise RuntimeError(
            "Cannot downgrade while treatment-free semantic mapping versions exist."
        )
    op.alter_column(table, "treatment_column", existing_type=sa.String(255), nullable=False)
    op.alter_column(table, "treatment_value", existing_type=sa.String(255), nullable=False)
    op.alter_column(table, "control_value", existing_type=sa.String(255), nullable=False)

    op.create_check_constraint(
        "ck_dataset_semantic_mappings_roles_distinct",
        table,
        """
        time_column <> unit_column
        AND time_column <> treatment_column
        AND time_column <> outcome_column
        AND unit_column <> treatment_column
        AND unit_column <> outcome_column
        AND treatment_column <> outcome_column
        AND (spend_column IS NULL OR (
            spend_column <> time_column
            AND spend_column <> unit_column
            AND spend_column <> treatment_column
            AND spend_column <> outcome_column
        ))
        """,
    )
    op.create_check_constraint(
        "ck_dataset_semantic_mappings_values_distinct",
        table,
        "lower(btrim(treatment_value)) <> lower(btrim(control_value))",
    )
