"""Snapshot statistical library versions on analysis runs.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "statistical_library_versions_json",
            sa.Text(),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_analysis_runs_statistical_library_versions_not_blank",
        "analysis_runs",
        (
            "statistical_library_versions_json IS NULL "
            "OR btrim(statistical_library_versions_json) <> ''"
        ),
    )
    op.create_check_constraint(
        "ck_analysis_runs_statistical_library_versions_object",
        "analysis_runs",
        (
            "statistical_library_versions_json IS NULL "
            "OR jsonb_typeof(statistical_library_versions_json::jsonb) = 'object'"
        ),
    )
    op.create_check_constraint(
        "ck_analysis_runs_statistical_library_versions_not_empty",
        "analysis_runs",
        (
            "statistical_library_versions_json IS NULL "
            "OR statistical_library_versions_json::jsonb <> '{}'::jsonb"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_runs_statistical_library_versions_not_empty",
        "analysis_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_analysis_runs_statistical_library_versions_object",
        "analysis_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_analysis_runs_statistical_library_versions_not_blank",
        "analysis_runs",
        type_="check",
    )
    op.drop_column(
        "analysis_runs",
        "statistical_library_versions_json",
    )
