from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from incrementality_api.infrastructure.database.base import Base
from incrementality_api.infrastructure.database.models.tenancy import TimestampMixin


class DataQualityAssessmentModel(TimestampMixin, Base):
    __tablename__ = "data_quality_assessments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "workspace_id", "project_id"],
            ["datasets.id", "datasets.workspace_id", "datasets.project_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_quality_score_range"),
        CheckConstraint("jsonb_typeof(findings) = 'array'", name="ck_quality_findings_array"),
        Index("ix_quality_dataset_created", "dataset_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    mapping_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimator_type: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    findings: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class ReportGenerationModel(TimestampMixin, Base):
    __tablename__ = "report_generations"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id", "format", "version", name="uq_report_run_format_version"
        ),
        ForeignKeyConstraint(
            ["analysis_run_id", "workspace_id", "project_id"],
            ["analysis_runs.id", "analysis_runs.workspace_id", "analysis_runs.project_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("format IN ('pdf','csv')", name="ck_report_format"),
        CheckConstraint(
            "status IN ('pending','running','succeeded','failed')", name="ck_report_status"
        ),
        CheckConstraint("version > 0", name="ck_report_version_positive"),
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= max_attempts", name="ck_report_attempts"
        ),
        CheckConstraint("jsonb_typeof(snapshot) = 'object'", name="ck_report_snapshot_object"),
        Index("ix_reports_scope_created", "workspace_id", "project_id", "created_at"),
        Index("ix_reports_pending", "status", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    analysis_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class ReportArtifactReconciliationRecordModel(Base):
    """Persist one append-only report artifact reconciliation result."""

    __tablename__ = "report_artifact_reconciliation_records"
    __table_args__ = (
        CheckConstraint(
            "checked >= 0",
            name="ck_report_reconciliation_checked_nonnegative",
        ),
        CheckConstraint(
            "missing >= 0 AND missing <= checked",
            name="ck_report_reconciliation_missing_range",
        ),
        CheckConstraint(
            "orphaned >= 0",
            name="ck_report_reconciliation_orphaned_nonnegative",
        ),
        CheckConstraint(
            "jsonb_typeof(orphaned_keys) = 'array'",
            name="ck_report_reconciliation_orphaned_keys_array",
        ),
        CheckConstraint(
            "jsonb_array_length(orphaned_keys) = orphaned",
            name="ck_report_reconciliation_orphaned_count",
        ),
        Index(
            "ix_report_reconciliation_executed_at",
            "executed_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    checked: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    missing: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    orphaned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    orphaned_keys: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )
