"""Snapshot immutable analysis estimand.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "estimand_snapshot_json",
            sa.Text(),
            nullable=True,
        ),
    )

    # Backfill only where existing persisted immutable lineage is sufficient
    # to reconstruct the estimand truthfully. Otherwise preserve NULL as legacy.
    op.execute(
        sa.text(
            """
            UPDATE analysis_runs
            SET estimand_snapshot_json = CASE
                WHEN estimator_type = 'difference_in_differences'
                     AND semantic_mapping_snapshot_json IS NOT NULL
                     AND treatment_control_snapshot_json IS NOT NULL THEN
                    jsonb_build_object(
                        'aggregation_method',
                            'difference_in_differences_interaction_coefficient',
                        'analysis_time_scope',
                            'post_treatment_period',
                        'comparison',
                            'control group counterfactual change',
                        'effect_scale',
                            'absolute_outcome_units',
                        'estimand_type',
                            'average_differential_change',
                        'estimator_type',
                            estimator_type,
                        'policy_target',
                            NULL,
                        'target_outcome',
                            semantic_mapping_snapshot_json::jsonb -> 'outcome_column',
                        'target_population',
                            'treated units in the post-treatment period',
                        'treated_population',
                            semantic_mapping_snapshot_json::jsonb -> 'treatment_value',
                        'unit_of_analysis',
                            'unit_period'
                    )::text

                WHEN estimator_type = 'synthetic_control'
                     AND semantic_mapping_snapshot_json IS NOT NULL
                     AND treatment_control_snapshot_json IS NOT NULL
                     AND jsonb_array_length(
                         treatment_control_snapshot_json::jsonb -> 'treated_units'
                     ) = 1 THEN
                    jsonb_build_object(
                        'aggregation_method',
                            'mean_post_treatment_treated_minus_synthetic_gap',
                        'analysis_time_scope',
                            'post_treatment_period',
                        'comparison',
                            'weighted synthetic counterfactual constructed from '
                            || 'the configured donor pool',
                        'effect_scale',
                            'absolute_outcome_units',
                        'estimand_type',
                            'average_post_treatment_gap',
                        'estimator_type',
                            estimator_type,
                        'policy_target',
                            NULL,
                        'target_outcome',
                            semantic_mapping_snapshot_json::jsonb -> 'outcome_column',
                        'target_population',
                            'treated unit in the post-treatment period',
                        'treated_population',
                            treatment_control_snapshot_json::jsonb
                                -> 'treated_units' -> 0,
                        'unit_of_analysis',
                            'treated_unit_period'
                    )::text

                WHEN estimator_type = 'geo_holdout'
                     AND semantic_mapping_snapshot_json IS NOT NULL
                     AND treatment_control_snapshot_json IS NOT NULL
                     AND jsonb_array_length(
                         treatment_control_snapshot_json::jsonb -> 'treated_units'
                     ) > 0 THEN
                    jsonb_build_object(
                        'aggregation_method',
                            'geo_difference_in_differences_interaction_coefficient',
                        'analysis_time_scope',
                            'post_treatment_period',
                        'comparison',
                            'configured holdout geographies under the '
                            || 'parallel-trends counterfactual',
                        'effect_scale',
                            'absolute_outcome_units_per_geo_period',
                        'estimand_type',
                            'average_incremental_geo_effect',
                        'estimator_type',
                            estimator_type,
                        'policy_target',
                            NULL,
                        'target_outcome',
                            semantic_mapping_snapshot_json::jsonb -> 'outcome_column',
                        'target_population',
                            'treated geographies in the post-treatment period',
                        'treated_population',
                            to_jsonb(
                                (
                                    SELECT string_agg(value, ',' ORDER BY ordinality)
                                    FROM jsonb_array_elements_text(
                                        treatment_control_snapshot_json::jsonb
                                            -> 'treated_units'
                                    ) WITH ORDINALITY AS units(value, ordinality)
                                )
                            ),
                        'unit_of_analysis',
                            'geography_period'
                    )::text

                WHEN estimator_type = 'marketing_mix_model'
                     AND semantic_mapping_snapshot_json IS NOT NULL THEN
                    jsonb_build_object(
                        'aggregation_method',
                            'sum_modeled_channel_contributions_divided_by_analysis_periods',
                        'analysis_time_scope',
                            'analysis_period',
                        'comparison',
                            'modeled baseline excluding media-channel contributions',
                        'effect_scale',
                            'absolute_outcome_units_per_period',
                        'estimand_type',
                            'average_modeled_media_contribution',
                        'estimator_type',
                            estimator_type,
                        'policy_target',
                            NULL,
                        'target_outcome',
                            semantic_mapping_snapshot_json::jsonb -> 'outcome_column',
                        'target_population',
                            'observed analysis periods',
                        'treated_population',
                            NULL,
                        'unit_of_analysis',
                            'time_period'
                    )::text

                WHEN estimator_type = 'off_policy_evaluation'
                     AND semantic_mapping_snapshot_json IS NOT NULL
                     AND treatment_control_snapshot_json IS NOT NULL
                     AND jsonb_typeof(
                         treatment_control_snapshot_json::jsonb -> 'policy_name'
                     ) = 'string'
                     AND jsonb_typeof(
                         configuration_json::jsonb -> 'reward_column'
                     ) = 'string' THEN
                    jsonb_build_object(
                        'aggregation_method',
                            concat(
                                COALESCE(
                                    configuration_json::jsonb ->> 'primary_method',
                                    'doubly_robust'
                                ),
                                '_mean_policy_value'
                            ),
                        'analysis_time_scope',
                            'analysis_period',
                        'comparison',
                            'logged behavior policy distribution used for off-policy correction',
                        'effect_scale',
                            'expected_reward_per_decision',
                        'estimand_type',
                            'target_policy_value',
                        'estimator_type',
                            estimator_type,
                        'policy_target',
                            treatment_control_snapshot_json::jsonb -> 'policy_name',
                        'target_outcome',
                            configuration_json::jsonb -> 'reward_column',
                        'target_population',
                            'logged decision population',
                        'treated_population',
                            NULL,
                        'unit_of_analysis',
                            'logged_decision'
                    )::text

                ELSE NULL
            END
            WHERE estimand_snapshot_json IS NULL
            """
        )
    )

    op.create_check_constraint(
        "ck_analysis_runs_estimand_snapshot_not_blank",
        "analysis_runs",
        (
            "estimand_snapshot_json IS NULL "
            "OR btrim(estimand_snapshot_json) <> ''"
        ),
    )

    op.create_check_constraint(
        "ck_analysis_runs_estimand_snapshot_object",
        "analysis_runs",
        (
            "estimand_snapshot_json IS NULL "
            "OR jsonb_typeof(estimand_snapshot_json::jsonb) = 'object'"
        ),
    )

    op.create_check_constraint(
        "ck_analysis_runs_estimand_snapshot_not_empty",
        "analysis_runs",
        (
            "estimand_snapshot_json IS NULL "
            "OR estimand_snapshot_json::jsonb <> '{}'::jsonb"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_runs_estimand_snapshot_not_empty",
        "analysis_runs",
        type_="check",
    )

    op.drop_constraint(
        "ck_analysis_runs_estimand_snapshot_object",
        "analysis_runs",
        type_="check",
    )

    op.drop_constraint(
        "ck_analysis_runs_estimand_snapshot_not_blank",
        "analysis_runs",
        type_="check",
    )

    op.drop_column(
        "analysis_runs",
        "estimand_snapshot_json",
    )
