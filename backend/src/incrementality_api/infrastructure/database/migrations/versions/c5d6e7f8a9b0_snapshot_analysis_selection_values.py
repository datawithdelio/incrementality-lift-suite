"""Snapshot analysis-selection values on analysis runs.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d6e7f8a9b0"
down_revision: str | None = "b4c5d6e7f8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMPTY_SELECTION = (
    '{"eligibility_filters":[],"excluded_geographies":[],'
    '"excluded_segments":[],"excluded_values":{},"geography_column":null,'
    '"included_values":{},"row_filters":[],"segment_column":null,'
    '"selected_geographies":[],"selected_segments":[]}'
)


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("analysis_selection_snapshot_json", sa.Text(), nullable=True),
    )
    # Selection criteria were not executed before this revision, so every existing
    # run truthfully used the complete eligible dataset after its analysis period.
    op.execute(
        sa.text(
            "UPDATE analysis_runs SET analysis_selection_snapshot_json = :snapshot"
        ).bindparams(snapshot=_EMPTY_SELECTION)
    )
    op.create_check_constraint(
        "ck_analysis_runs_selection_snapshot_not_blank",
        "analysis_runs",
        (
            "analysis_selection_snapshot_json IS NULL "
            "OR btrim(analysis_selection_snapshot_json) <> ''"
        ),
    )
    op.create_check_constraint(
        "ck_analysis_runs_selection_snapshot_object",
        "analysis_runs",
        (
            "analysis_selection_snapshot_json IS NULL "
            "OR jsonb_typeof(analysis_selection_snapshot_json::jsonb) = 'object'"
        ),
    )
    op.create_check_constraint(
        "ck_analysis_runs_selection_snapshot_not_empty",
        "analysis_runs",
        (
            "analysis_selection_snapshot_json IS NULL "
            "OR analysis_selection_snapshot_json::jsonb <> '{}'::jsonb"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_runs_selection_snapshot_not_empty", "analysis_runs", type_="check"
    )
    op.drop_constraint(
        "ck_analysis_runs_selection_snapshot_object", "analysis_runs", type_="check"
    )
    op.drop_constraint(
        "ck_analysis_runs_selection_snapshot_not_blank", "analysis_runs", type_="check"
    )
    op.drop_column("analysis_runs", "analysis_selection_snapshot_json")
