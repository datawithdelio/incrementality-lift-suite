"""Add report artifact integrity metadata.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""

import sqlalchemy as sa
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_generations",
        sa.Column(
            "artifact_byte_size",
            sa.BigInteger(),
            nullable=True,
        ),
    )
    op.add_column(
        "report_generations",
        sa.Column(
            "artifact_checksum_sha256",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_report_artifact_integrity",
        "report_generations",
        (
            "("
            "artifact_byte_size IS NULL "
            "AND artifact_checksum_sha256 IS NULL"
            ") OR ("
            "artifact_byte_size > 0 "
            "AND artifact_checksum_sha256 "
            "~ '^[0-9a-f]{64}$'"
            ")"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_report_artifact_integrity",
        "report_generations",
        type_="check",
    )
    op.drop_column(
        "report_generations",
        "artifact_checksum_sha256",
    )
    op.drop_column(
        "report_generations",
        "artifact_byte_size",
    )
