"""Create structured canonical analysis results.

Revision ID: 9d2c4f6a8b10
Revises: 4c6d7e8f9a0b
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9d2c4f6a8b10"
down_revision: str | None = "4c6d7e8f9a0b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("semantic_mapping_id", sa.Uuid(), nullable=False),
        sa.Column("semantic_mapping_version", sa.Integer(), nullable=False),
        sa.Column("estimator_type", sa.String(length=64), nullable=False),
        sa.Column("estimator_version", sa.String(length=255), nullable=False),
        sa.Column("library_name", sa.String(length=255), nullable=False),
        sa.Column("library_version", sa.String(length=255), nullable=False),
        sa.Column("effect", sa.Float(), nullable=False),
        sa.Column("standard_error", sa.Float(), nullable=False),
        sa.Column("p_value", sa.Float(), nullable=False),
        sa.Column("confidence_interval_low", sa.Float(), nullable=False),
        sa.Column("confidence_interval_high", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.BigInteger(), nullable=False),
        sa.Column("diagnostics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("incremental_outcome", sa.Float(), nullable=True),
        sa.Column("relative_lift", sa.Float(), nullable=True),
        sa.Column("incremental_revenue", sa.Float(), nullable=True),
        sa.Column("incremental_conversions", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "btrim(estimator_version) <> ''", name="ck_analysis_results_estimator_version"
        ),
        sa.CheckConstraint("btrim(library_name) <> ''", name="ck_analysis_results_library_name"),
        sa.CheckConstraint(
            "btrim(library_version) <> ''", name="ck_analysis_results_library_version"
        ),
        sa.CheckConstraint(
            "standard_error >= 0", name="ck_analysis_results_standard_error_nonnegative"
        ),
        sa.CheckConstraint(
            "p_value >= 0 AND p_value <= 1", name="ck_analysis_results_p_value_range"
        ),
        sa.CheckConstraint(
            "confidence_interval_low <= effect AND effect <= confidence_interval_high",
            name="ck_analysis_results_confidence_interval",
        ),
        sa.CheckConstraint("sample_size > 0", name="ck_analysis_results_sample_size_positive"),
        sa.CheckConstraint(
            "jsonb_typeof(diagnostics) = 'object'", name="ck_analysis_results_diagnostics_object"
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id", "workspace_id", "project_id"],
            ["analysis_runs.id", "analysis_runs.workspace_id", "analysis_runs.project_id"],
            name="fk_analysis_results_run_scope",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", name="uq_analysis_results_analysis_run_id"),
    )
    op.create_index(
        "ix_analysis_results_workspace_project", "analysis_results", ["workspace_id", "project_id"]
    )
    op.create_index("ix_analysis_results_dataset_id", "analysis_results", ["dataset_id"])
    op.create_index("ix_analysis_results_created_at", "analysis_results", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_analysis_results_created_at", table_name="analysis_results")
    op.drop_index("ix_analysis_results_dataset_id", table_name="analysis_results")
    op.drop_index("ix_analysis_results_workspace_project", table_name="analysis_results")
    op.drop_table("analysis_results")
