import json
from dataclasses import replace

import pytest

from incrementality_api.application.analysis_execution.estimation import (
    GeoHoldoutInput,
    MarketingMixInput,
    OffPolicyEvaluationInput,
    PermanentEstimationError,
    SyntheticControlInput,
)
from incrementality_api.application.analysis_execution.input_loading import (
    GeoHoldoutInputBuilder,
    MarketingMixInputBuilder,
    OffPolicyEvaluationInputBuilder,
    SyntheticControlInputBuilder,
)
from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)

from .test_input_loading import build_metadata

ROWS = (
    {"date": "2026-01-01", "market": "north", "treated": "no", "revenue": "10"},
    {"date": "2026-01-02", "market": "north", "treated": "no", "revenue": "11"},
    {"date": "2026-01-01", "market": "south", "treated": "yes", "revenue": "12"},
    {"date": "2026-01-02", "market": "south", "treated": "yes", "revenue": "18"},
)


def test_builds_synthetic_control_panel_from_semantic_mapping() -> None:
    _job, metadata = build_metadata()
    run = replace(metadata.run, estimator_type=AnalysisEstimatorType.SYNTHETIC_CONTROL)

    result = SyntheticControlInputBuilder().build(rows=ROWS, mapping=metadata.mapping, run=run)

    assert isinstance(result, SyntheticControlInput)
    assert len(result.observations) == 4


def test_builds_geo_holdout_with_coordinates_and_spillovers() -> None:
    _job, metadata = build_metadata()
    configuration = {
        "intervention_time": "2026-01-02T00:00:00+00:00",
        "outcome_kind": "revenue",
        "geo_coordinates": {
            "north": {"latitude": 40, "longitude": -74},
            "south": {"latitude": 33, "longitude": -84},
        },
        "spillover_pairs": [["south", "north"]],
    }
    run = replace(
        metadata.run,
        estimator_type=AnalysisEstimatorType.GEO_HOLDOUT,
        configuration_json=json.dumps(configuration),
    )

    result = GeoHoldoutInputBuilder().build(rows=ROWS, mapping=metadata.mapping, run=run)

    assert isinstance(result, GeoHoldoutInput)
    assert result.coordinates["north"].latitude == 40
    assert result.spillover_pairs == (("south", "north"),)


def test_builds_aggregated_marketing_mix_channels() -> None:
    _job, metadata = build_metadata()
    mapping = replace(
        metadata.mapping,
        outcome_column="conversions",
        spend_column="total_spend",
        covariate_columns=("sessions", "holiday", "promotion"),
    )
    media_channels = (
        "paid_search_spend",
        "social_spend",
        "tv_spend",
        "display_spend",
        "email_spend",
    )
    rows = (
        {
            "date": f"2026-01-{day:02d}",
            "market": "all",
            "treated": "no",
            "conversions": str(100 + day),
            "total_spend": str(75 + day * 5),
            "paid_search_spend": str(20 + day),
            "social_spend": str(10 + day),
            "tv_spend": str(15 + day),
            "display_spend": str(12 + day),
            "email_spend": str(8 + day),
            "sessions": str(1_000 + day),
            "holiday": "0",
            "promotion": "1",
        }
        for day in range(1, 13)
    )
    run = replace(
        metadata.run,
        estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
        configuration_json=json.dumps(
            {
                "media_channels": list(media_channels),
                "control_columns": ["sessions", "holiday", "promotion"],
                "aggregate_spend_column": "total_spend",
                "adstock_decay": dict.fromkeys(media_channels, 0.5),
                "saturation_half_spend": dict.fromkeys(media_channels, 20),
                "seasonality_period": 7,
                "outcome_kind": "conversions",
            }
        ),
    )

    result = MarketingMixInputBuilder().build(rows=tuple(rows), mapping=mapping, run=run)

    assert isinstance(result, MarketingMixInput)
    assert result.outcome_kind == "conversions"
    assert result.observations[0].channel_spend == {
        "paid_search_spend": 21.0,
        "social_spend": 11.0,
        "tv_spend": 16.0,
        "display_spend": 13.0,
        "email_spend": 9.0,
    }
    assert result.observations[0].controls == {
        "sessions": 1001.0,
        "holiday": 0.0,
        "promotion": 1.0,
    }
    assert "total_spend" not in result.observations[0].channel_spend


def test_rejects_mmm_outcome_kind_that_disagrees_with_mapped_outcome() -> None:
    _job, metadata = build_metadata()
    mapping = replace(
        metadata.mapping,
        outcome_column="conversions",
        spend_column="total_spend",
        covariate_columns=("sessions",),
    )
    rows = tuple(
        {
            "date": f"2026-01-{day:02d}",
            "conversions": str(100 + day),
            "paid_search_spend": str(20 + day),
            "sessions": str(1_000 + day),
        }
        for day in range(1, 13)
    )
    run = replace(
        metadata.run,
        estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
        configuration_json=json.dumps(
            {
                "media_channels": ["paid_search_spend"],
                "control_columns": ["sessions"],
                "aggregate_spend_column": "total_spend",
                "adstock_decay": {"paid_search_spend": 0.5},
                "saturation_half_spend": {"paid_search_spend": 20},
                "seasonality_period": 7,
                "outcome_kind": "revenue",
            }
        ),
    )

    with pytest.raises(
        PermanentEstimationError,
        match="outcome_kind must match the mapped outcome column",
    ):
        MarketingMixInputBuilder().build(rows=rows, mapping=mapping, run=run)


def test_builds_off_policy_input_from_custom_policy_columns() -> None:
    _job, metadata = build_metadata()
    rows = (
        {
            "reward": "4",
            "behavior": "0.5",
            "target": "0.75",
            "observed_prediction": "3.5",
            "target_prediction": "3.8",
        },
        {
            "reward": "2",
            "behavior": "0.4",
            "target": "0.25",
            "observed_prediction": "2.1",
            "target_prediction": "2.4",
        },
    )
    period = AnalysisPeriodSnapshot.from_configuration(
        AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        {"analysis_start_date": "2026-01-01", "analysis_end_date": "2026-01-31"},
    )
    selection = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        configuration={},
        semantic_mapping=metadata.mapping,
    )
    assignment = TreatmentControlSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        configuration={
            "policy_name": "growth_policy",
            "behavior_propensity_column": "behavior",
            "target_propensity_column": "target",
        },
        semantic_mapping=metadata.mapping,
        analysis_period=period,
        analysis_selection=selection,
    )
    run = replace(
        metadata.run,
        estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        analysis_period_snapshot=period,
        analysis_selection_snapshot=selection,
        treatment_control_snapshot=assignment,
        configuration_json=json.dumps(
            {
                "policy_name": "mutable_policy",
                "reward_column": "reward",
                "behavior_propensity_column": "wrong_behavior",
                "target_propensity_column": "wrong_target",
                "observed_action_expected_reward_column": "observed_prediction",
                "target_policy_expected_reward_column": "target_prediction",
                "primary_method": "doubly_robust",
            }
        ),
    )

    result = OffPolicyEvaluationInputBuilder().build(rows=rows, mapping=metadata.mapping, run=run)

    assert isinstance(result, OffPolicyEvaluationInput)
    assert result.policy_name == "growth_policy"
    assert result.observations[0].target_probability == 0.75
    assert result.observations[0].observed_action_expected_reward == 3.5
    assert result.observations[0].target_policy_expected_reward == 3.8
