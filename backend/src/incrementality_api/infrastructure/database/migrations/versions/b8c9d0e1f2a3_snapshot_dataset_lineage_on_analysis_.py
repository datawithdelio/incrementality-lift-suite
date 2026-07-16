"""Snapshot dataset lineage on analysis runs.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "dataset_checksum_sha256",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.add_column(
        "analysis_runs",
        sa.Column(
            "dataset_byte_size",
            sa.Integer(),
            nullable=True,
        ),
    )

    # Backfill historical runs from the exact dataset record
    # referenced by each analysis run.
    op.execute(
        sa.text(
            """
            UPDATE analysis_runs AS analysis_run
            SET
                dataset_checksum_sha256 = dataset.checksum_sha256,
                dataset_byte_size = dataset.byte_size
            FROM datasets AS dataset
            WHERE dataset.id = analysis_run.dataset_id
              AND dataset.workspace_id = analysis_run.workspace_id
              AND dataset.project_id = analysis_run.project_id
            """
        )
    )

    op.alter_column(
        "analysis_runs",
        "dataset_checksum_sha256",
        existing_type=sa.String(length=64),
        nullable=False,
    )

    op.alter_column(
        "analysis_runs",
        "dataset_byte_size",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_check_constraint(
        "ck_analysis_runs_dataset_checksum_sha256_format",
        "analysis_runs",
        "dataset_checksum_sha256 ~ '^[0-9a-f]{64}$'",
    )

    op.create_check_constraint(
        "ck_analysis_runs_dataset_byte_size_positive",
        "analysis_runs",
        "dataset_byte_size > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_runs_dataset_byte_size_positive",
        "analysis_runs",
        type_="check",
    )

    op.drop_constraint(
        "ck_analysis_runs_dataset_checksum_sha256_format",
        "analysis_runs",
        type_="check",
    )

    op.drop_column(
        "analysis_runs",
        "dataset_byte_size",
    )

    op.drop_column(
        "analysis_runs",
        "dataset_checksum_sha256",
    )
