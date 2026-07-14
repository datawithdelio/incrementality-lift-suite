"""Restrict datasets to CSV.

Revision ID: 1b2b0f2d0fb1
Revises: 3dc95c920c85
"""

from collections.abc import Sequence

from alembic import op

revision: str = "1b2b0f2d0fb1"
down_revision: str | None = "3dc95c920c85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_datasets_media_type",
        "datasets",
        type_="check",
    )

    op.create_check_constraint(
        "ck_datasets_media_type",
        "datasets",
        "media_type IN ('text/csv')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_datasets_media_type",
        "datasets",
        type_="check",
    )

    op.create_check_constraint(
        "ck_datasets_media_type",
        "datasets",
        ("media_type IN ('text/csv', 'application/vnd.apache.parquet')"),
    )
