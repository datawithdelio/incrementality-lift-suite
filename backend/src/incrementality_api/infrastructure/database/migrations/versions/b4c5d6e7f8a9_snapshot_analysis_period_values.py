"""Snapshot analysis-period values on analysis runs.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4c5d6e7f8a9"
down_revision: str | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("analysis_period_snapshot_json", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_analysis_runs_period_snapshot_not_blank",
        "analysis_runs",
        (
            "analysis_period_snapshot_json IS NULL "
            "OR btrim(analysis_period_snapshot_json) <> ''"
        ),
    )
    op.create_check_constraint(
        "ck_analysis_runs_period_snapshot_object",
        "analysis_runs",
        (
            "analysis_period_snapshot_json IS NULL "
            "OR jsonb_typeof(analysis_period_snapshot_json::jsonb) = 'object'"
        ),
    )
    op.create_check_constraint(
        "ck_analysis_runs_period_snapshot_not_empty",
        "analysis_runs",
        (
            "analysis_period_snapshot_json IS NULL "
            "OR analysis_period_snapshot_json::jsonb <> '{}'::jsonb"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_runs_period_snapshot_not_empty", "analysis_runs", type_="check"
    )
    op.drop_constraint(
        "ck_analysis_runs_period_snapshot_object", "analysis_runs", type_="check"
    )
    op.drop_constraint(
        "ck_analysis_runs_period_snapshot_not_blank", "analysis_runs", type_="check"
    )
    op.drop_column("analysis_runs", "analysis_period_snapshot_json")
