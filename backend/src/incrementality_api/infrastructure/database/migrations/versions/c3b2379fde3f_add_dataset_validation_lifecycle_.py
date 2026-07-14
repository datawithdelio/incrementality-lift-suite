"""Add dataset validation lifecycle metadata.

Revision ID: c3b2379fde3f
Revises: b1e4c9f6b7d1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3b2379fde3f"
down_revision: str | Sequence[str] | None = "b1e4c9f6b7d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LIFECYCLE_METADATA_CONDITION = """
(
    status = 'pending_upload'
    AND uploaded_at IS NULL
    AND validation_started_at IS NULL
    AND validation_completed_at IS NULL
    AND row_count IS NULL
    AND column_count IS NULL
    AND failure_reason IS NULL
)
OR
(
    status = 'uploaded'
    AND uploaded_at IS NOT NULL
    AND validation_started_at IS NULL
    AND validation_completed_at IS NULL
    AND row_count IS NULL
    AND column_count IS NULL
    AND failure_reason IS NULL
)
OR
(
    status = 'validating'
    AND uploaded_at IS NOT NULL
    AND validation_started_at IS NOT NULL
    AND validation_completed_at IS NULL
    AND row_count IS NULL
    AND column_count IS NULL
    AND failure_reason IS NULL
)
OR
(
    status = 'ready'
    AND uploaded_at IS NOT NULL
    AND validation_started_at IS NOT NULL
    AND validation_completed_at IS NOT NULL
    AND row_count IS NOT NULL
    AND column_count IS NOT NULL
    AND failure_reason IS NULL
)
OR
(
    status = 'failed'
    AND uploaded_at IS NOT NULL
    AND validation_started_at IS NOT NULL
    AND validation_completed_at IS NOT NULL
    AND row_count IS NULL
    AND column_count IS NULL
    AND failure_reason IS NOT NULL
)
"""


def upgrade() -> None:
    op.add_column(
        "datasets",
        sa.Column(
            "validation_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_datasets_validation_started_requires_upload",
        "datasets",
        ("validation_started_at IS NULL OR uploaded_at IS NOT NULL"),
    )

    op.create_check_constraint(
        "ck_datasets_validation_started_not_before_upload",
        "datasets",
        ("validation_started_at IS NULL OR validation_started_at >= uploaded_at"),
    )

    op.create_check_constraint(
        "ck_datasets_validation_completed_requires_start",
        "datasets",
        ("validation_completed_at IS NULL OR validation_started_at IS NOT NULL"),
    )

    op.create_check_constraint(
        "ck_datasets_validation_completed_not_before_start",
        "datasets",
        ("validation_completed_at IS NULL OR validation_completed_at >= validation_started_at"),
    )

    op.create_check_constraint(
        "ck_datasets_lifecycle_metadata",
        "datasets",
        LIFECYCLE_METADATA_CONDITION,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_datasets_lifecycle_metadata",
        "datasets",
        type_="check",
    )

    op.drop_constraint(
        "ck_datasets_validation_completed_not_before_start",
        "datasets",
        type_="check",
    )

    op.drop_constraint(
        "ck_datasets_validation_completed_requires_start",
        "datasets",
        type_="check",
    )

    op.drop_constraint(
        "ck_datasets_validation_started_not_before_upload",
        "datasets",
        type_="check",
    )

    op.drop_constraint(
        "ck_datasets_validation_started_requires_upload",
        "datasets",
        type_="check",
    )

    op.drop_column(
        "datasets",
        "validation_started_at",
    )
