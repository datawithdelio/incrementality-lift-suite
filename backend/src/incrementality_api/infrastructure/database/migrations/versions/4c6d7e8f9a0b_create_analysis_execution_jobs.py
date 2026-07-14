"""Create durable analysis execution jobs.

Revision ID: 4c6d7e8f9a0b
Revises: 8f1c2d3e4a5b
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4c6d7e8f9a0b"
down_revision: str | Sequence[str] | None = "8f1c2d3e4a5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_analysis_runs_id_workspace_project",
        "analysis_runs",
        [
            "id",
            "workspace_id",
            "project_id",
        ],
    )

    op.create_table(
        "analysis_execution_jobs",
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
            "analysis_run_id",
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
            sa.String(length=2_000),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            """
            status IN (
                'pending',
                'running',
                'succeeded',
                'dead_letter'
            )
            """,
            name="ck_analysis_execution_jobs_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name=("ck_analysis_execution_jobs_attempt_nonnegative"),
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name=("ck_analysis_execution_jobs_max_attempts_positive"),
        ),
        sa.CheckConstraint(
            "attempt_count <= max_attempts",
            name=("ck_analysis_execution_jobs_attempt_within_limit"),
        ),
        sa.CheckConstraint(
            ("last_error IS NULL OR btrim(last_error) <> ''"),
            name=("ck_analysis_execution_jobs_error_not_blank"),
        ),
        sa.CheckConstraint(
            "available_at >= created_at",
            name=("ck_analysis_execution_jobs_available_after_create"),
        ),
        sa.CheckConstraint(
            ("claimed_at IS NULL OR claimed_at >= available_at"),
            name=("ck_analysis_execution_jobs_claim_after_available"),
        ),
        sa.CheckConstraint(
            """
            completed_at IS NULL
            OR
            (
                claimed_at IS NOT NULL
                AND completed_at >= claimed_at
            )
            """,
            name=("ck_analysis_execution_jobs_completion_after_claim"),
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
            name=("ck_analysis_execution_jobs_lifecycle_metadata"),
        ),
        sa.ForeignKeyConstraint(
            [
                "analysis_run_id",
                "workspace_id",
                "project_id",
            ],
            [
                "analysis_runs.id",
                "analysis_runs.workspace_id",
                "analysis_runs.project_id",
            ],
            name=("fk_analysis_execution_jobs_run_scope"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            name=("uq_analysis_execution_jobs_analysis_run_id"),
        ),
    )

    op.create_index(
        ("ix_analysis_execution_jobs_claimable"),
        "analysis_execution_jobs",
        [
            "status",
            "available_at",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        ("ix_analysis_execution_jobs_stale_running"),
        "analysis_execution_jobs",
        [
            "status",
            "claimed_at",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        ("ix_analysis_execution_jobs_workspace_id"),
        "analysis_execution_jobs",
        ["workspace_id"],
        unique=False,
    )

    op.create_index(
        ("ix_analysis_execution_jobs_project_id"),
        "analysis_execution_jobs",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        ("ix_analysis_execution_jobs_project_id"),
        table_name="analysis_execution_jobs",
    )

    op.drop_index(
        ("ix_analysis_execution_jobs_workspace_id"),
        table_name="analysis_execution_jobs",
    )

    op.drop_index(
        ("ix_analysis_execution_jobs_stale_running"),
        table_name="analysis_execution_jobs",
    )

    op.drop_index(
        ("ix_analysis_execution_jobs_claimable"),
        table_name="analysis_execution_jobs",
    )

    op.drop_table(
        "analysis_execution_jobs",
    )

    op.drop_constraint(
        "uq_analysis_runs_id_workspace_project",
        "analysis_runs",
        type_="unique",
    )
