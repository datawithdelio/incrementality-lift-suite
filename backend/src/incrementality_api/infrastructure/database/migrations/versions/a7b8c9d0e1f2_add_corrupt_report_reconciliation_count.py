"""Add corrupt report reconciliation count.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_artifact_reconciliation_records",
        sa.Column(
            "corrupt",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_report_reconciliation_corrupt_nonnegative",
        "report_artifact_reconciliation_records",
        "corrupt >= 0",
    )
    op.create_check_constraint(
        "ck_report_reconciliation_inconsistency_range",
        "report_artifact_reconciliation_records",
        "missing + corrupt <= checked",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_report_reconciliation_inconsistency_range",
        "report_artifact_reconciliation_records",
        type_="check",
    )
    op.drop_constraint(
        "ck_report_reconciliation_corrupt_nonnegative",
        "report_artifact_reconciliation_records",
        type_="check",
    )
    op.drop_column(
        "report_artifact_reconciliation_records",
        "corrupt",
    )
