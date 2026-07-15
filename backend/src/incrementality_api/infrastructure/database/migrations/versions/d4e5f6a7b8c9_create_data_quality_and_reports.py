"""Create durable data quality assessments and report jobs.

Revision ID: d4e5f6a7b8c9
Revises: 9d2c4f6a8b10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "9d2c4f6a8b10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_quality_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("mapping_version", sa.Integer(), nullable=True),
        sa.Column("estimator_type", sa.String(64), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("ready", sa.Boolean(), nullable=False),
        sa.Column("findings", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_quality_score_range"),
        sa.CheckConstraint("jsonb_typeof(findings) = 'array'", name="ck_quality_findings_array"),
        sa.ForeignKeyConstraint(
            ["dataset_id", "workspace_id", "project_id"],
            ["datasets.id", "datasets.workspace_id", "datasets.project_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_quality_dataset_created", "data_quality_assessments", ["dataset_id", "created_at"]
    )
    op.create_table(
        "report_generations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("format IN ('pdf','csv')", name="ck_report_format"),
        sa.CheckConstraint(
            "status IN ('pending','running','succeeded','failed')", name="ck_report_status"
        ),
        sa.CheckConstraint("version > 0", name="ck_report_version_positive"),
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= max_attempts", name="ck_report_attempts"
        ),
        sa.CheckConstraint("jsonb_typeof(snapshot) = 'object'", name="ck_report_snapshot_object"),
        sa.ForeignKeyConstraint(
            ["analysis_run_id", "workspace_id", "project_id"],
            ["analysis_runs.id", "analysis_runs.workspace_id", "analysis_runs.project_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id", "format", "version", name="uq_report_run_format_version"
        ),
    )
    op.create_index(
        "ix_reports_scope_created",
        "report_generations",
        ["workspace_id", "project_id", "created_at"],
    )
    op.create_index("ix_reports_pending", "report_generations", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("report_generations")
    op.drop_table("data_quality_assessments")
