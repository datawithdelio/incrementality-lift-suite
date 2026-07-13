from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from incrementality_api.infrastructure.database.base import Base
from incrementality_api.infrastructure.database.models.tenancy import (
    TimestampMixin,
)


class ProjectModel(TimestampMixin, Base):
    """Persistent workspace-scoped project."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "slug",
            name="uq_projects_workspace_slug",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_projects_name_not_blank",
        ),
        CheckConstraint(
            "btrim(slug) <> ''",
            name="ck_projects_slug_not_blank",
        ),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_projects_status",
        ),
        CheckConstraint(
            "("
            "(status = 'active' AND archived_at IS NULL)"
            " OR "
            "(status = 'archived' AND archived_at IS NOT NULL)"
            ")",
            name="ck_projects_archive_consistency",
        ),
        Index(
            "ix_projects_workspace_id",
            "workspace_id",
        ),
        Index(
            "ix_projects_created_by_user_id",
            "created_by_user_id",
        ),
        Index(
            "ix_projects_workspace_status",
            "workspace_id",
            "status",
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

    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
