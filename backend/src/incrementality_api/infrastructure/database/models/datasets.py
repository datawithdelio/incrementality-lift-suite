from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
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


class DatasetModel(TimestampMixin, Base):
    """Persistent metadata for one project dataset."""

    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint(
            "storage_key",
            name="uq_datasets_storage_key",
        ),
        CheckConstraint(
            "btrim(source_filename) <> ''",
            name="ck_datasets_source_filename_not_blank",
        ),
        CheckConstraint(
            "btrim(storage_key) <> ''",
            name="ck_datasets_storage_key_not_blank",
        ),
        CheckConstraint(
            "media_type IN ('text/csv', 'application/vnd.apache.parquet')",
            name="ck_datasets_media_type",
        ),
        CheckConstraint(
            "byte_size > 0",
            name="ck_datasets_byte_size_positive",
        ),
        CheckConstraint(
            "checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_datasets_checksum_sha256",
        ),
        CheckConstraint(
            "status IN ('pending_upload', 'uploaded', 'validating', 'ready', 'failed')",
            name="ck_datasets_status",
        ),
        CheckConstraint(
            "row_count IS NULL OR row_count >= 0",
            name="ck_datasets_row_count_nonnegative",
        ),
        CheckConstraint(
            "column_count IS NULL OR column_count > 0",
            name="ck_datasets_column_count_positive",
        ),
        CheckConstraint(
            "failure_reason IS NULL OR btrim(failure_reason) <> ''",
            name="ck_datasets_failure_reason_not_blank",
        ),
        Index(
            "ix_datasets_workspace_id",
            "workspace_id",
        ),
        Index(
            "ix_datasets_project_id",
            "project_id",
        ),
        Index(
            "ix_datasets_created_by_user_id",
            "created_by_user_id",
        ),
        Index(
            "ix_datasets_project_status",
            "project_id",
            "status",
        ),
        Index(
            "ix_datasets_workspace_status",
            "workspace_id",
            "status",
        ),
        Index(
            "ix_datasets_checksum_sha256",
            "checksum_sha256",
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

    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    source_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    media_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    byte_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    validation_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    row_count: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    column_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )
