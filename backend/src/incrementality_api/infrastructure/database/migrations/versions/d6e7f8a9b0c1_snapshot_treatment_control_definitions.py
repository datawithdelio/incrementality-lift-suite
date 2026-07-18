"""Snapshot immutable treatment and control definitions.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: str | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("treatment_control_snapshot_json", sa.Text(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE analysis_runs
            SET treatment_control_snapshot_json = CASE
                WHEN estimator_type = 'marketing_mix_model' THEN
                    jsonb_build_object(
                        'estimator_type', estimator_type,
                        'assignment_rule', 'not_applicable',
                        'treatment_column', NULL,
                        'treatment_value', NULL,
                        'control_value', NULL,
                        'intervention_date', NULL,
                        'treated_units', '[]'::jsonb,
                        'control_units', '[]'::jsonb,
                        'excluded_treatment_units', '[]'::jsonb,
                        'excluded_control_units', '[]'::jsonb,
                        'treatment_cohort', NULL,
                        'control_eligibility_rules', '[]'::jsonb,
                        'policy_name', NULL,
                        'behavior_propensity_column', NULL,
                        'target_propensity_column', NULL
                    )::text
                WHEN estimator_type = 'off_policy_evaluation'
                     AND jsonb_typeof(configuration_json::jsonb -> 'policy_name') = 'string'
                     AND jsonb_typeof(
                         configuration_json::jsonb -> 'behavior_propensity_column'
                     ) = 'string'
                     AND jsonb_typeof(
                         configuration_json::jsonb -> 'target_propensity_column'
                     ) = 'string' THEN
                    jsonb_build_object(
                        'estimator_type', estimator_type,
                        'assignment_rule', 'logged_policy_propensity',
                        'treatment_column', NULL,
                        'treatment_value', NULL,
                        'control_value', NULL,
                        'intervention_date', NULL,
                        'treated_units', '[]'::jsonb,
                        'control_units', '[]'::jsonb,
                        'excluded_treatment_units', '[]'::jsonb,
                        'excluded_control_units', '[]'::jsonb,
                        'treatment_cohort', NULL,
                        'control_eligibility_rules', '[]'::jsonb,
                        'policy_name', configuration_json::jsonb -> 'policy_name',
                        'behavior_propensity_column',
                            configuration_json::jsonb -> 'behavior_propensity_column',
                        'target_propensity_column',
                            configuration_json::jsonb -> 'target_propensity_column'
                    )::text
                WHEN estimator_type IN (
                         'difference_in_differences', 'synthetic_control', 'geo_holdout'
                     )
                     AND semantic_mapping_snapshot_json IS NOT NULL
                     AND analysis_period_snapshot_json IS NOT NULL
                     AND (
                         estimator_type = 'difference_in_differences'
                         OR (
                             estimator_type = 'synthetic_control'
                             AND jsonb_typeof(
                                 configuration_json::jsonb -> 'treated_unit'
                             ) = 'string'
                             AND jsonb_typeof(configuration_json::jsonb -> 'donor_pool') = 'array'
                             AND jsonb_array_length(
                                 configuration_json::jsonb -> 'donor_pool'
                             ) >= 2
                         )
                         OR (
                             estimator_type = 'geo_holdout'
                             AND jsonb_typeof(
                                 configuration_json::jsonb -> 'treated_geographies'
                             ) = 'array'
                             AND jsonb_array_length(
                                 configuration_json::jsonb -> 'treated_geographies'
                             ) > 0
                             AND jsonb_typeof(
                                 configuration_json::jsonb -> 'control_geographies'
                             ) = 'array'
                             AND jsonb_array_length(
                                 configuration_json::jsonb -> 'control_geographies'
                             ) > 0
                         )
                     ) THEN
                    jsonb_build_object(
                        'estimator_type', estimator_type,
                        'assignment_rule', CASE estimator_type
                            WHEN 'difference_in_differences'
                                THEN 'mapped_binary_at_intervention'
                            WHEN 'synthetic_control'
                                THEN 'one_treated_unit_with_donor_pool'
                            ELSE 'explicit_geo_holdout'
                        END,
                        'treatment_column',
                            semantic_mapping_snapshot_json::jsonb -> 'treatment_column',
                        'treatment_value',
                            semantic_mapping_snapshot_json::jsonb -> 'treatment_value',
                        'control_value',
                            semantic_mapping_snapshot_json::jsonb -> 'control_value',
                        'intervention_date',
                            analysis_period_snapshot_json::jsonb -> 'intervention_date',
                        'treated_units', CASE estimator_type
                            WHEN 'synthetic_control' THEN
                                jsonb_build_array(configuration_json::jsonb -> 'treated_unit')
                            WHEN 'geo_holdout' THEN
                                configuration_json::jsonb -> 'treated_geographies'
                            ELSE '[]'::jsonb
                        END,
                        'control_units', CASE estimator_type
                            WHEN 'synthetic_control' THEN
                                configuration_json::jsonb -> 'donor_pool'
                            WHEN 'geo_holdout' THEN
                                configuration_json::jsonb -> 'control_geographies'
                            ELSE '[]'::jsonb
                        END,
                        'excluded_treatment_units', COALESCE(
                            configuration_json::jsonb -> 'excluded_treatment_units', '[]'::jsonb
                        ),
                        'excluded_control_units', COALESCE(
                            configuration_json::jsonb -> 'excluded_control_units', '[]'::jsonb
                        ),
                        'treatment_cohort', configuration_json::jsonb -> 'treatment_cohort',
                        'control_eligibility_rules', COALESCE(
                            configuration_json::jsonb -> 'control_eligibility_rules', '[]'::jsonb
                        ),
                        'policy_name', NULL,
                        'behavior_propensity_column', NULL,
                        'target_propensity_column', NULL
                    )::text
                ELSE NULL
            END
            WHERE treatment_control_snapshot_json IS NULL
            """
        )
    )
    op.create_check_constraint(
        "ck_analysis_runs_treatment_control_snapshot_not_blank",
        "analysis_runs",
        (
            "treatment_control_snapshot_json IS NULL "
            "OR btrim(treatment_control_snapshot_json) <> ''"
        ),
    )
    op.create_check_constraint(
        "ck_analysis_runs_treatment_control_snapshot_object",
        "analysis_runs",
        (
            "treatment_control_snapshot_json IS NULL "
            "OR jsonb_typeof(treatment_control_snapshot_json::jsonb) = 'object'"
        ),
    )
    op.create_check_constraint(
        "ck_analysis_runs_treatment_control_snapshot_not_empty",
        "analysis_runs",
        (
            "treatment_control_snapshot_json IS NULL "
            "OR treatment_control_snapshot_json::jsonb <> '{}'::jsonb"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_runs_treatment_control_snapshot_not_empty",
        "analysis_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_analysis_runs_treatment_control_snapshot_object",
        "analysis_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_analysis_runs_treatment_control_snapshot_not_blank",
        "analysis_runs",
        type_="check",
    )
    op.drop_column("analysis_runs", "treatment_control_snapshot_json")
