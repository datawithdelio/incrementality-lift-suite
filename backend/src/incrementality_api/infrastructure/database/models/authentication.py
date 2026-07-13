from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from incrementality_api.infrastructure.database.base import Base


class UserCredentialModel(Base):
    """Persistent password credential for one user."""

    __tablename__ = "user_credentials"
    __table_args__ = (
        CheckConstraint(
            "btrim(password_hash) <> ''",
            name="ck_user_credentials_password_hash_not_blank",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuthSessionModel(Base):
    """Revocable server-side authentication session."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="uq_auth_sessions_token_hash",
        ),
        CheckConstraint(
            "char_length(token_hash) = 64",
            name="ck_auth_sessions_token_hash_length",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_auth_sessions_expiration",
        ),
        Index(
            "ix_auth_sessions_user_id",
            "user_id",
        ),
        Index(
            "ix_auth_sessions_expires_at",
            "expires_at",
        ),
        Index(
            "ix_auth_sessions_user_revoked",
            "user_id",
            "revoked_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
