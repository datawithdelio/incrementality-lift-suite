"""Create reproducible causal-analysis runs.

Revision ID: 8f1c2d3e4a5b
Revises: 73b5d8c4da97
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8f1c2d3e4a5b"
down_revision: str | Sequence[str] | None = "73b5d8c4da97"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_datasets_id_workspace_project",
        "datasets",
        [
            "id",
            "workspace_id",
            "project_id",
        ],
    )

    op.create_unique_constraint(
        ("uq_dataset_semantic_mappings_id_dataset_version"),
        "dataset_semantic_mappings",
        [
            "id",
            "dataset_id",
            "version",
        ],
    )

    op.create_table(
        "analysis_runs",
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
            "semantic_mapping_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "semantic_mapping_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "estimator_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "estimator_version",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "configuration_json",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "failure_reason",
            sa.String(length=2_000),
            nullable=True,
        ),
        sa.Column(
            "cancellation_reason",
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
            "semantic_mapping_version > 0",
            name=("ck_analysis_runs_mapping_version_positive"),
        ),
        sa.CheckConstraint(
            """
            estimator_type IN (
                'difference_in_differences',
                'synthetic_control',
                'geo_holdout',
                'marketing_mix_model',
                'off_policy_evaluation'
            )
            """,
            name="ck_analysis_runs_estimator_type",
        ),
        sa.CheckConstraint(
            "btrim(estimator_version) <> ''",
            name=("ck_analysis_runs_estimator_version_not_blank"),
        ),
        sa.CheckConstraint(
            "btrim(configuration_json) <> ''",
            name=("ck_analysis_runs_configuration_not_blank"),
        ),
        sa.CheckConstraint(
            ("jsonb_typeof(configuration_json::jsonb) = 'object'"),
            name=("ck_analysis_runs_configuration_object"),
        ),
        sa.CheckConstraint(
            """
            status IN (
                'queued',
                'running',
                'succeeded',
                'failed',
                'cancelled'
            )
            """,
            name="ck_analysis_runs_status",
        ),
        sa.CheckConstraint(
            ("failure_reason IS NULL OR btrim(failure_reason) <> ''"),
            name=("ck_analysis_runs_failure_reason_not_blank"),
        ),
        sa.CheckConstraint(
            ("cancellation_reason IS NULL OR btrim(cancellation_reason) <> ''"),
            name=("ck_analysis_runs_cancellation_reason_not_blank"),
        ),
        sa.CheckConstraint(
            ("started_at IS NULL OR started_at >= created_at"),
            name=("ck_analysis_runs_start_after_create"),
        ),
        sa.CheckConstraint(
            ("completed_at IS NULL OR completed_at >= created_at"),
            name=("ck_analysis_runs_completion_after_create"),
        ),
        sa.CheckConstraint(
            """
            completed_at IS NULL
            OR started_at IS NULL
            OR completed_at >= started_at
            """,
            name=("ck_analysis_runs_completion_after_start"),
        ),
        sa.CheckConstraint(
            """
            (
                status = 'queued'
                AND started_at IS NULL
                AND completed_at IS NULL
                AND failure_reason IS NULL
                AND cancellation_reason IS NULL
            )
            OR
            (
                status = 'running'
                AND started_at IS NOT NULL
                AND completed_at IS NULL
                AND failure_reason IS NULL
                AND cancellation_reason IS NULL
            )
            OR
            (
                status = 'succeeded'
                AND started_at IS NOT NULL
                AND completed_at IS NOT NULL
                AND failure_reason IS NULL
                AND cancellation_reason IS NULL
            )
            OR
            (
                status = 'failed'
                AND started_at IS NOT NULL
                AND completed_at IS NOT NULL
                AND failure_reason IS NOT NULL
                AND cancellation_reason IS NULL
            )
            OR
            (
                status = 'cancelled'
                AND completed_at IS NOT NULL
                AND failure_reason IS NULL
                AND cancellation_reason IS NOT NULL
            )
            """,
            name=("ck_analysis_runs_lifecycle_metadata"),
        ),
        sa.ForeignKeyConstraint(
            [
                "dataset_id",
                "workspace_id",
                "project_id",
            ],
            [
                "datasets.id",
                "datasets.workspace_id",
                "datasets.project_id",
            ],
            name="fk_analysis_runs_dataset_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            [
                "semantic_mapping_id",
                "dataset_id",
                "semantic_mapping_version",
            ],
            [
                "dataset_semantic_mappings.id",
                "dataset_semantic_mappings.dataset_id",
                "dataset_semantic_mappings.version",
            ],
            name=("fk_analysis_runs_semantic_mapping_snapshot"),
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_analysis_runs_creator",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        ("ix_analysis_runs_workspace_project_created_at"),
        "analysis_runs",
        [
            "workspace_id",
            "project_id",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_analysis_runs_dataset_created_at",
        "analysis_runs",
        [
            "dataset_id",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_analysis_runs_status_created_at",
        "analysis_runs",
        [
            "status",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_analysis_runs_semantic_mapping_id",
        "analysis_runs",
        ["semantic_mapping_id"],
        unique=False,
    )

    op.create_index(
        "ix_analysis_runs_created_by_user_id",
        "analysis_runs",
        ["created_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analysis_runs_created_by_user_id",
        table_name="analysis_runs",
    )

    op.drop_index(
        "ix_analysis_runs_semantic_mapping_id",
        table_name="analysis_runs",
    )

    op.drop_index(
        "ix_analysis_runs_status_created_at",
        table_name="analysis_runs",
    )

    op.drop_index(
        "ix_analysis_runs_dataset_created_at",
        table_name="analysis_runs",
    )

    op.drop_index(
        ("ix_analysis_runs_workspace_project_created_at"),
        table_name="analysis_runs",
    )

    op.drop_table(
        "analysis_runs",
    )

    op.drop_constraint(
        ("uq_dataset_semantic_mappings_id_dataset_version"),
        "dataset_semantic_mappings",
        type_="unique",
    )

    op.drop_constraint(
        "uq_datasets_id_workspace_project",
        "datasets",
        type_="unique",
    )
