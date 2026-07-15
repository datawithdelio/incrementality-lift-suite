import json
from dataclasses import replace

from incrementality_api.application.analysis_execution.estimation import (
    GeoHoldoutInput,
    MarketingMixInput,
    OffPolicyEvaluationInput,
    SyntheticControlInput,
)
from incrementality_api.application.analysis_execution.input_loading import (
    GeoHoldoutInputBuilder,
    MarketingMixInputBuilder,
    OffPolicyEvaluationInputBuilder,
    SyntheticControlInputBuilder,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

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
        spend_column="search",
        covariate_columns=("social",),
    )
    rows = (
        {
            "date": f"2026-01-{day:02d}",
            "market": "all",
            "treated": "no",
            "revenue": str(100 + day),
            "search": str(20 + day),
            "social": str(10 + day),
        }
        for day in range(1, 13)
    )
    run = replace(
        metadata.run,
        estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
        configuration_json=json.dumps(
            {
                "adstock_decay": {"search": 0.5, "social": 0.3},
                "saturation_half_spend": {"search": 20, "social": 10},
                "seasonality_period": 7,
                "outcome_kind": "revenue",
            }
        ),
    )

    result = MarketingMixInputBuilder().build(rows=tuple(rows), mapping=mapping, run=run)

    assert isinstance(result, MarketingMixInput)
    assert result.observations[0].channel_spend == {"search": 21.0, "social": 11.0}


def test_builds_off_policy_input_from_custom_policy_columns() -> None:
    _job, metadata = build_metadata()
    rows = (
        {"reward": "4", "behavior": "0.5", "target": "0.75", "prediction": "3.5"},
        {"reward": "2", "behavior": "0.4", "target": "0.25", "prediction": "2.1"},
    )
    run = replace(
        metadata.run,
        estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        configuration_json=json.dumps(
            {
                "policy_name": "growth_policy",
                "reward_column": "reward",
                "behavior_propensity_column": "behavior",
                "target_propensity_column": "target",
                "expected_reward_column": "prediction",
                "primary_method": "doubly_robust",
            }
        ),
    )

    result = OffPolicyEvaluationInputBuilder().build(rows=rows, mapping=metadata.mapping, run=run)

    assert isinstance(result, OffPolicyEvaluationInput)
    assert result.policy_name == "growth_policy"
    assert result.observations[0].target_probability == 0.75
