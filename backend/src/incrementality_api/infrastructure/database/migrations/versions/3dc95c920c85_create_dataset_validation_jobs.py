"""Create durable dataset validation jobs.

Revision ID: 3dc95c920c85
Revises: c3b2379fde3f
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3dc95c920c85"
down_revision: str | Sequence[str] | None = "c3b2379fde3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dataset_validation_jobs",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_error",
            sa.String(length=2000),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            ("status IN ('pending', 'running', 'succeeded', 'dead_letter')"),
            name="ck_dataset_validation_jobs_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name=("ck_dataset_validation_jobs_attempt_nonnegative"),
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name=("ck_dataset_validation_jobs_max_attempts_positive"),
        ),
        sa.CheckConstraint(
            "attempt_count <= max_attempts",
            name=("ck_dataset_validation_jobs_attempt_within_limit"),
        ),
        sa.CheckConstraint(
            ("last_error IS NULL OR btrim(last_error) <> ''"),
            name=("ck_dataset_validation_jobs_error_not_blank"),
        ),
        sa.CheckConstraint(
            "available_at >= created_at",
            name=("ck_dataset_validation_jobs_available_after_create"),
        ),
        sa.CheckConstraint(
            ("claimed_at IS NULL OR claimed_at >= available_at"),
            name=("ck_dataset_validation_jobs_claim_after_available"),
        ),
        sa.CheckConstraint(
            ("completed_at IS NULL OR (claimed_at IS NOT NULL AND completed_at >= claimed_at)"),
            name=("ck_dataset_validation_jobs_completion_after_claim"),
        ),
        sa.CheckConstraint(
            """
            (
                status = 'pending'
                AND claimed_at IS NULL
                AND completed_at IS NULL
                AND attempt_count < max_attempts
            )
            OR
            (
                status = 'running'
                AND claimed_at IS NOT NULL
                AND completed_at IS NULL
                AND attempt_count >= 1
            )
            OR
            (
                status = 'succeeded'
                AND claimed_at IS NOT NULL
                AND completed_at IS NOT NULL
                AND attempt_count >= 1
                AND last_error IS NULL
            )
            OR
            (
                status = 'dead_letter'
                AND claimed_at IS NOT NULL
                AND completed_at IS NOT NULL
                AND attempt_count >= 1
                AND last_error IS NOT NULL
            )
            """,
            name=("ck_dataset_validation_jobs_lifecycle_metadata"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            name=("uq_dataset_validation_jobs_dataset_id"),
        ),
    )

    op.create_index(
        "ix_dataset_validation_jobs_claimable",
        "dataset_validation_jobs",
        [
            "status",
            "available_at",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_dataset_validation_jobs_workspace_id",
        "dataset_validation_jobs",
        ["workspace_id"],
        unique=False,
    )

    op.create_index(
        "ix_dataset_validation_jobs_project_id",
        "dataset_validation_jobs",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dataset_validation_jobs_project_id",
        table_name="dataset_validation_jobs",
    )

    op.drop_index(
        "ix_dataset_validation_jobs_workspace_id",
        table_name="dataset_validation_jobs",
    )

    op.drop_index(
        "ix_dataset_validation_jobs_claimable",
        table_name="dataset_validation_jobs",
    )

    op.drop_table(
        "dataset_validation_jobs",
    )
