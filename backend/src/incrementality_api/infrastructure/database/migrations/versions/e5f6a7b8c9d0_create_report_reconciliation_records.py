"""Create durable report artifact reconciliation records.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_artifact_reconciliation_records",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "checked",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "missing",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "orphaned",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "orphaned_keys",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "checked >= 0",
            name="ck_report_reconciliation_checked_nonnegative",
        ),
        sa.CheckConstraint(
            "missing >= 0 AND missing <= checked",
            name="ck_report_reconciliation_missing_range",
        ),
        sa.CheckConstraint(
            "orphaned >= 0",
            name="ck_report_reconciliation_orphaned_nonnegative",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(orphaned_keys) = 'array'",
            name="ck_report_reconciliation_orphaned_keys_array",
        ),
        sa.CheckConstraint(
            "jsonb_array_length(orphaned_keys) = orphaned",
            name="ck_report_reconciliation_orphaned_count",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_report_reconciliation_executed_at",
        "report_artifact_reconciliation_records",
        ["executed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_reconciliation_executed_at",
        table_name="report_artifact_reconciliation_records",
    )
    op.drop_table(
        "report_artifact_reconciliation_records"
    )
