"""create datasets table

Revision ID: b1e4c9f6b7d1
Revises: ad22a7a7f284
Create Date: 2026-07-13 19:17:11.851631
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1e4c9f6b7d1"
down_revision: str | None = "ad22a7a7f284"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
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
            "created_by_user_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "source_filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "storage_key",
            sa.String(length=1024),
            nullable=False,
        ),
        sa.Column(
            "media_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "byte_size",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "checksum_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "validation_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "row_count",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "column_count",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "failure_reason",
            sa.String(length=2000),
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
            "btrim(source_filename) <> ''",
            name="ck_datasets_source_filename_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(storage_key) <> ''",
            name="ck_datasets_storage_key_not_blank",
        ),
        sa.CheckConstraint(
            "checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_datasets_checksum_sha256",
        ),
        sa.CheckConstraint(
            "failure_reason IS NULL OR btrim(failure_reason) <> ''",
            name="ck_datasets_failure_reason_not_blank",
        ),
        sa.CheckConstraint(
            "media_type IN ('text/csv', 'application/vnd.apache.parquet')",
            name="ck_datasets_media_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending_upload', 'uploaded', 'validating', 'ready', 'failed')",
            name="ck_datasets_status",
        ),
        sa.CheckConstraint(
            "byte_size > 0",
            name="ck_datasets_byte_size_positive",
        ),
        sa.CheckConstraint(
            "column_count IS NULL OR column_count > 0",
            name="ck_datasets_column_count_positive",
        ),
        sa.CheckConstraint(
            "row_count IS NULL OR row_count >= 0",
            name="ck_datasets_row_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_datasets_storage_key",
        ),
    )

    op.create_index(
        "ix_datasets_checksum_sha256",
        "datasets",
        ["checksum_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_datasets_created_by_user_id",
        "datasets",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_datasets_project_id",
        "datasets",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_datasets_project_status",
        "datasets",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_datasets_workspace_id",
        "datasets",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_datasets_workspace_status",
        "datasets",
        ["workspace_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_datasets_workspace_status",
        table_name="datasets",
    )
    op.drop_index(
        "ix_datasets_workspace_id",
        table_name="datasets",
    )
    op.drop_index(
        "ix_datasets_project_status",
        table_name="datasets",
    )
    op.drop_index(
        "ix_datasets_project_id",
        table_name="datasets",
    )
    op.drop_index(
        "ix_datasets_created_by_user_id",
        table_name="datasets",
    )
    op.drop_index(
        "ix_datasets_checksum_sha256",
        table_name="datasets",
    )
    op.drop_table("datasets")
