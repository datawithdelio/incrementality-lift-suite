from dataclasses import FrozenInstanceError

import pytest

from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.estimand_snapshot import EstimandSnapshot
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)


def test_estimand_snapshot_is_immutable_and_has_deterministic_representation() -> None:
    snapshot = EstimandSnapshot(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        estimand_type="average_differential_change",
        target_outcome="revenue",
        target_population="treated units in the post-treatment period",
        treated_population="units assigned to treatment",
        comparison="control-unit outcome change under the parallel-trends counterfactual",
        effect_scale="absolute_outcome_units",
        aggregation_method="difference_in_differences_interaction_coefficient",
        analysis_time_scope="post_treatment_period",
        unit_of_analysis="unit_period",
        policy_target=None,
    )

    assert snapshot.as_dict() == {
        "aggregation_method": "difference_in_differences_interaction_coefficient",
        "analysis_time_scope": "post_treatment_period",
        "comparison": (
            "control-unit outcome change under the parallel-trends counterfactual"
        ),
        "effect_scale": "absolute_outcome_units",
        "estimand_type": "average_differential_change",
        "estimator_type": "difference_in_differences",
        "policy_target": None,
        "target_outcome": "revenue",
        "target_population": "treated units in the post-treatment period",
        "treated_population": "units assigned to treatment",
        "unit_of_analysis": "unit_period",
    }

    with pytest.raises(FrozenInstanceError):
        snapshot.estimand_type = "changed"  # type: ignore[misc]


def test_derives_difference_in_differences_estimand_from_validated_snapshots() -> None:
    configuration_json = """
    {
        "analysis_start_date": "2025-01-01",
        "analysis_end_date": "2025-03-31",
        "intervention_date": "2025-02-01"
    }
    """

    semantic_mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="customer_id",
        treatment_column="experiment_group",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="treated",
        control_value="control",
    )

    analysis_period = AnalysisPeriodSnapshot.from_configuration_json(
        AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        configuration_json,
    )

    analysis_selection = AnalysisSelectionSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
    )

    treatment_control = TreatmentControlSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
    )

    snapshot = EstimandSnapshot.from_validated_run_configuration(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
        treatment_control=treatment_control,
        serialized=configuration_json,
    )

    assert snapshot.as_dict() == {
        "aggregation_method": "difference_in_differences_interaction_coefficient",
        "analysis_time_scope": "post_treatment_period",
        "comparison": "control group counterfactual change",
        "effect_scale": "absolute_outcome_units",
        "estimand_type": "average_differential_change",
        "estimator_type": "difference_in_differences",
        "policy_target": None,
        "target_outcome": "revenue",
        "target_population": "treated units in the post-treatment period",
        "treated_population": "treated",
        "unit_of_analysis": "unit_period",
    }


def test_derives_synthetic_control_estimand_from_validated_snapshots() -> None:
    configuration_json = """
    {
        "analysis_start_date": "2024-01-01",
        "analysis_end_date": "2024-12-31",
        "intervention_date": "2024-07-01",
        "treated_unit": "Northstar",
        "donor_pool": ["Meadow", "Riverton"]
    }
    """

    semantic_mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="group",
        outcome_column="failed_checkouts_per_1000_sessions",
        spend_column=None,
        covariate_columns=(),
        treatment_value="treated",
        control_value="control",
    )

    analysis_period = AnalysisPeriodSnapshot.from_configuration_json(
        AnalysisEstimatorType.SYNTHETIC_CONTROL,
        configuration_json,
    )

    analysis_selection = AnalysisSelectionSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.SYNTHETIC_CONTROL,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
    )

    treatment_control = TreatmentControlSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.SYNTHETIC_CONTROL,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
    )

    snapshot = EstimandSnapshot.from_validated_run_configuration(
        estimator_type=AnalysisEstimatorType.SYNTHETIC_CONTROL,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
        treatment_control=treatment_control,
        serialized=configuration_json,
    )

    assert snapshot.as_dict() == {
        "aggregation_method": "mean_post_treatment_treated_minus_synthetic_gap",
        "analysis_time_scope": "post_treatment_period",
        "comparison": (
            "weighted synthetic counterfactual constructed from "
            "the configured donor pool"
        ),
        "effect_scale": "absolute_outcome_units",
        "estimand_type": "average_post_treatment_gap",
        "estimator_type": "synthetic_control",
        "policy_target": None,
        "target_outcome": "failed_checkouts_per_1000_sessions",
        "target_population": "treated unit in the post-treatment period",
        "treated_population": "Northstar",
        "unit_of_analysis": "treated_unit_period",
    }


def test_derives_geo_holdout_estimand_from_validated_snapshots() -> None:
    configuration_json = """
    {
        "analysis_start_date": "2025-01-01",
        "analysis_end_date": "2025-06-30",
        "intervention_date": "2025-04-01",
        "treated_geographies": ["New York", "Boston"],
        "control_geographies": ["Philadelphia", "Baltimore"]
    }
    """

    semantic_mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="geography",
        treatment_column="assignment",
        outcome_column="conversions",
        spend_column=None,
        covariate_columns=(),
        treatment_value="treatment",
        control_value="holdout",
    )

    analysis_period = AnalysisPeriodSnapshot.from_configuration_json(
        AnalysisEstimatorType.GEO_HOLDOUT,
        configuration_json,
    )

    analysis_selection = AnalysisSelectionSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.GEO_HOLDOUT,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
    )

    treatment_control = TreatmentControlSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.GEO_HOLDOUT,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
    )

    snapshot = EstimandSnapshot.from_validated_run_configuration(
        estimator_type=AnalysisEstimatorType.GEO_HOLDOUT,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
        treatment_control=treatment_control,
        serialized=configuration_json,
    )

    assert snapshot.as_dict() == {
        "aggregation_method": "geo_difference_in_differences_interaction_coefficient",
        "analysis_time_scope": "post_treatment_period",
        "comparison": "configured holdout geographies under the parallel-trends counterfactual",
        "effect_scale": "absolute_outcome_units_per_geo_period",
        "estimand_type": "average_incremental_geo_effect",
        "estimator_type": "geo_holdout",
        "policy_target": None,
        "target_outcome": "conversions",
        "target_population": "treated geographies in the post-treatment period",
        "treated_population": "Boston,New York",
        "unit_of_analysis": "geography_period",
    }


def test_derives_marketing_mix_model_estimand_from_validated_snapshots() -> None:
    configuration_json = """
    {
        "analysis_start_date": "2024-01-01",
        "analysis_end_date": "2024-12-31",
        "seasonality_period": 52,
        "outcome_kind": "revenue",
        "adstock_decay": {
            "paid_search_spend": 0.5,
            "social_spend": 0.4
        },
        "saturation_half_spend": {
            "paid_search_spend": 1000.0,
            "social_spend": 750.0
        }
    }
    """

    semantic_mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="campaign_group",
        outcome_column="revenue",
        spend_column="paid_search_spend",
        covariate_columns=("social_spend",),
        treatment_value="treated",
        control_value="control",
    )

    analysis_period = AnalysisPeriodSnapshot.from_configuration_json(
        AnalysisEstimatorType.MARKETING_MIX_MODEL,
        configuration_json,
    )

    analysis_selection = AnalysisSelectionSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
    )

    treatment_control = TreatmentControlSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
    )

    snapshot = EstimandSnapshot.from_validated_run_configuration(
        estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
        treatment_control=treatment_control,
        serialized=configuration_json,
    )

    assert snapshot.as_dict() == {
        "aggregation_method": (
            "sum_modeled_channel_contributions_divided_by_analysis_periods"
        ),
        "analysis_time_scope": "analysis_period",
        "comparison": "modeled baseline excluding media-channel contributions",
        "effect_scale": "absolute_outcome_units_per_period",
        "estimand_type": "average_modeled_media_contribution",
        "estimator_type": "marketing_mix_model",
        "policy_target": None,
        "target_outcome": "revenue",
        "target_population": "observed analysis periods",
        "treated_population": None,
        "unit_of_analysis": "time_period",
    }


def test_derives_off_policy_evaluation_estimand_from_validated_snapshots() -> None:
    configuration_json = """
    {
        "analysis_start_date": "2025-01-01",
        "analysis_end_date": "2025-06-30",
        "policy_name": "new_recommendation_policy",
        "behavior_propensity_column": "behavior_probability",
        "target_propensity_column": "target_probability",
        "reward_column": "reward",
        "observed_action_expected_reward_column": "observed_expected_reward",
        "target_policy_expected_reward_column": "target_expected_reward",
        "primary_method": "doubly_robust"
    }
    """

    semantic_mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="decision_id",
        treatment_column="action",
        outcome_column="reward",
        spend_column=None,
        covariate_columns=(),
        treatment_value="selected",
        control_value="not_selected",
    )

    analysis_period = AnalysisPeriodSnapshot.from_configuration_json(
        AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        configuration_json,
    )

    analysis_selection = AnalysisSelectionSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
    )

    treatment_control = TreatmentControlSnapshot.from_configuration_json(
        estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        serialized=configuration_json,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
    )

    snapshot = EstimandSnapshot.from_validated_run_configuration(
        estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        semantic_mapping=semantic_mapping,
        analysis_period=analysis_period,
        analysis_selection=analysis_selection,
        treatment_control=treatment_control,
        serialized=configuration_json,
    )

    assert snapshot.as_dict() == {
        "aggregation_method": "doubly_robust_mean_policy_value",
        "analysis_time_scope": "analysis_period",
        "comparison": (
            "logged behavior policy distribution used for off-policy correction"
        ),
        "effect_scale": "expected_reward_per_decision",
        "estimand_type": "target_policy_value",
        "estimator_type": "off_policy_evaluation",
        "policy_target": "new_recommendation_policy",
        "target_outcome": "reward",
        "target_population": "logged decision population",
        "treated_population": None,
        "unit_of_analysis": "logged_decision",
    }


def test_estimand_snapshot_has_deterministic_canonical_json_round_trip() -> None:
    snapshot = EstimandSnapshot(
        estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        estimand_type="target_policy_value",
        target_outcome="reward",
        target_population="logged decision population",
        treated_population=None,
        comparison="logged behavior policy distribution used for off-policy correction",
        effect_scale="expected_reward_per_decision",
        aggregation_method="doubly_robust_mean_policy_value",
        analysis_time_scope="analysis_period",
        unit_of_analysis="logged_decision",
        policy_target="new_recommendation_policy",
    )

    assert snapshot.canonical_json == (
        '{"aggregation_method":"doubly_robust_mean_policy_value",'
        '"analysis_time_scope":"analysis_period",'
        '"comparison":"logged behavior policy distribution used for off-policy correction",'
        '"effect_scale":"expected_reward_per_decision",'
        '"estimand_type":"target_policy_value",'
        '"estimator_type":"off_policy_evaluation",'
        '"policy_target":"new_recommendation_policy",'
        '"target_outcome":"reward",'
        '"target_population":"logged decision population",'
        '"treated_population":null,'
        '"unit_of_analysis":"logged_decision"}'
    )

    restored = EstimandSnapshot.from_json(snapshot.canonical_json)

    assert restored == snapshot
