"""Snapshot semantic mapping values on analysis runs.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("semantic_mapping_snapshot_json", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_analysis_runs_mapping_snapshot_not_blank",
        "analysis_runs",
        (
            "semantic_mapping_snapshot_json IS NULL "
            "OR btrim(semantic_mapping_snapshot_json) <> ''"
        ),
    )
    op.execute(
        """
        UPDATE analysis_runs AS run
        SET semantic_mapping_snapshot_json = jsonb_build_object(
            'time_column', mapping.time_column,
            'unit_column', mapping.unit_column,
            'treatment_column', mapping.treatment_column,
            'outcome_column', mapping.outcome_column,
            'spend_column', mapping.spend_column,
            'covariate_columns', COALESCE(
                (
                    SELECT jsonb_agg(
                        covariate.normalized_column_name
                        ORDER BY covariate.ordinal_position
                    )
                    FROM dataset_mapping_covariates AS covariate
                    WHERE covariate.mapping_id = mapping.id
                      AND covariate.dataset_id = mapping.dataset_id
                ),
                '[]'::jsonb
            ),
            'treatment_value', mapping.treatment_value,
            'control_value', mapping.control_value
        )::text
        FROM dataset_semantic_mappings AS mapping
        WHERE run.semantic_mapping_id = mapping.id
          AND run.dataset_id = mapping.dataset_id
          AND run.semantic_mapping_version = mapping.version
          AND run.semantic_mapping_snapshot_json IS NULL
        """
    )
    op.create_check_constraint(
        "ck_analysis_runs_mapping_snapshot_object",
        "analysis_runs",
        (
            "semantic_mapping_snapshot_json IS NULL "
            "OR jsonb_typeof(semantic_mapping_snapshot_json::jsonb) = 'object'"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_runs_mapping_snapshot_object",
        "analysis_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_analysis_runs_mapping_snapshot_not_blank",
        "analysis_runs",
        type_="check",
    )
    op.drop_column("analysis_runs", "semantic_mapping_snapshot_json")
