"""Snapshot analysis runtime versions.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "application_version",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "analysis_runs",
        sa.Column(
            "source_revision",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_analysis_runs_application_version_not_blank",
        "analysis_runs",
        ("application_version IS NULL OR btrim(application_version) <> ''"),
    )

    op.create_check_constraint(
        "ck_analysis_runs_source_revision_not_blank",
        "analysis_runs",
        ("source_revision IS NULL OR btrim(source_revision) <> ''"),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_runs_source_revision_not_blank",
        "analysis_runs",
        type_="check",
    )

    op.drop_constraint(
        "ck_analysis_runs_application_version_not_blank",
        "analysis_runs",
        type_="check",
    )

    op.drop_column(
        "analysis_runs",
        "source_revision",
    )

    op.drop_column(
        "analysis_runs",
        "application_version",
    )
