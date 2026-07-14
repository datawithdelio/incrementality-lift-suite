from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from incrementality_api.infrastructure.database.base import Base
from incrementality_api.infrastructure.database.models.tenancy import TimestampMixin


class AnalysisResultModel(TimestampMixin, Base):
    """Persist one canonical structured result for an analysis run."""

    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint("analysis_run_id", name="uq_analysis_results_analysis_run_id"),
        CheckConstraint(
            "btrim(estimator_version) <> ''", name="ck_analysis_results_estimator_version"
        ),
        CheckConstraint("btrim(library_name) <> ''", name="ck_analysis_results_library_name"),
        CheckConstraint("btrim(library_version) <> ''", name="ck_analysis_results_library_version"),
        CheckConstraint(
            "standard_error >= 0", name="ck_analysis_results_standard_error_nonnegative"
        ),
        CheckConstraint("p_value >= 0 AND p_value <= 1", name="ck_analysis_results_p_value_range"),
        CheckConstraint(
            "confidence_interval_low <= effect AND effect <= confidence_interval_high",
            name="ck_analysis_results_confidence_interval",
        ),
        CheckConstraint("sample_size > 0", name="ck_analysis_results_sample_size_positive"),
        CheckConstraint(
            "jsonb_typeof(diagnostics) = 'object'", name="ck_analysis_results_diagnostics_object"
        ),
        ForeignKeyConstraint(
            ["analysis_run_id", "workspace_id", "project_id"],
            ["analysis_runs.id", "analysis_runs.workspace_id", "analysis_runs.project_id"],
            name="fk_analysis_results_run_scope",
            ondelete="CASCADE",
        ),
        Index("ix_analysis_results_workspace_project", "workspace_id", "project_id"),
        Index("ix_analysis_results_dataset_id", "dataset_id"),
        Index("ix_analysis_results_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    analysis_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    semantic_mapping_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    semantic_mapping_version: Mapped[int] = mapped_column(nullable=False)
    estimator_type: Mapped[str] = mapped_column(String(64), nullable=False)
    estimator_version: Mapped[str] = mapped_column(String(255), nullable=False)
    library_name: Mapped[str] = mapped_column(String(255), nullable=False)
    library_version: Mapped[str] = mapped_column(String(255), nullable=False)
    effect: Mapped[float] = mapped_column(Float, nullable=False)
    standard_error: Mapped[float] = mapped_column(Float, nullable=False)
    p_value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_interval_low: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_interval_high: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    diagnostics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    incremental_outcome: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_lift: Mapped[float | None] = mapped_column(Float, nullable=True)
    incremental_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    incremental_conversions: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
