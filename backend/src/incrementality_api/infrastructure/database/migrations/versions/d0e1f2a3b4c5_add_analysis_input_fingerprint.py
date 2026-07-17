"""Add analysis input fingerprint.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "input_fingerprint_sha256",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_analysis_runs_input_fingerprint_sha256_format",
        "analysis_runs",
        ("input_fingerprint_sha256 IS NULL OR input_fingerprint_sha256 ~ '^[0-9a-f]{64}$'"),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_runs_input_fingerprint_sha256_format",
        "analysis_runs",
        type_="check",
    )

    op.drop_column(
        "analysis_runs",
        "input_fingerprint_sha256",
    )
