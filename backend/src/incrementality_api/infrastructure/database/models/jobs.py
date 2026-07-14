from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from incrementality_api.infrastructure.database.base import Base
from incrementality_api.infrastructure.database.models.tenancy import (
    TimestampMixin,
)


class DatasetValidationJobModel(TimestampMixin, Base):
    """Durable PostgreSQL job for validating one dataset."""

    __tablename__ = "dataset_validation_jobs"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            name=("uq_dataset_validation_jobs_dataset_id"),
        ),
        CheckConstraint(
            ("status IN ('pending', 'running', 'succeeded', 'dead_letter')"),
            name="ck_dataset_validation_jobs_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name=("ck_dataset_validation_jobs_attempt_nonnegative"),
        ),
        CheckConstraint(
            "max_attempts > 0",
            name=("ck_dataset_validation_jobs_max_attempts_positive"),
        ),
        CheckConstraint(
            "attempt_count <= max_attempts",
            name=("ck_dataset_validation_jobs_attempt_within_limit"),
        ),
        CheckConstraint(
            ("last_error IS NULL OR btrim(last_error) <> ''"),
            name=("ck_dataset_validation_jobs_error_not_blank"),
        ),
        CheckConstraint(
            "available_at >= created_at",
            name=("ck_dataset_validation_jobs_available_after_create"),
        ),
        CheckConstraint(
            ("claimed_at IS NULL OR claimed_at >= available_at"),
            name=("ck_dataset_validation_jobs_claim_after_available"),
        ),
        CheckConstraint(
            ("completed_at IS NULL OR (claimed_at IS NOT NULL AND completed_at >= claimed_at)"),
            name=("ck_dataset_validation_jobs_completion_after_claim"),
        ),
        CheckConstraint(
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
        Index(
            "ix_dataset_validation_jobs_claimable",
            "status",
            "available_at",
            "created_at",
        ),
        Index(
            "ix_dataset_validation_jobs_workspace_id",
            "workspace_id",
        ),
        Index(
            "ix_dataset_validation_jobs_project_id",
            "project_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "workspaces.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "datasets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )
