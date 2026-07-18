import json

import pytest

from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)


def _mapping() -> SemanticMappingSnapshot:
    return SemanticMappingSnapshot.create(
        time_column="event_date",
        unit_column="market",
        treatment_column="variant",
        outcome_column="revenue",
        spend_column="spend",
        covariate_columns=["population"],
        treatment_value="treated",
        control_value="control",
    )


def _period(estimator_type: AnalysisEstimatorType) -> AnalysisPeriodSnapshot:
    return AnalysisPeriodSnapshot.from_configuration(
        estimator_type,
        {
            "analysis_start_date": "2025-01-01",
            "analysis_end_date": "2025-03-31",
            "intervention_date": "2025-02-01",
        },
    )


def _selection(estimator_type: AnalysisEstimatorType) -> AnalysisSelectionSnapshot:
    return AnalysisSelectionSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={},
        semantic_mapping=_mapping(),
    )


def test_marketing_mix_has_an_explicit_not_applicable_assignment() -> None:
    assert TreatmentControlSnapshot.not_applicable().as_dict() == {
        "estimator_type": "marketing_mix_model",
        "assignment_rule": "not_applicable",
        "treatment_column": None,
        "treatment_value": None,
        "control_value": None,
        "intervention_date": None,
        "treated_units": [],
        "control_units": [],
        "excluded_treatment_units": [],
        "excluded_control_units": [],
        "treatment_cohort": None,
        "control_eligibility_rules": [],
        "policy_name": None,
        "behavior_propensity_column": None,
        "target_propensity_column": None,
    }


def test_did_preserves_mapped_assignment_and_intervention_date() -> None:
    estimator_type = AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES

    snapshot = TreatmentControlSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={},
        semantic_mapping=_mapping(),
        analysis_period=_period(estimator_type),
        analysis_selection=_selection(estimator_type),
    )

    assert snapshot.assignment_rule == "mapped_binary_at_intervention"
    assert snapshot.treatment_column == "variant"
    assert snapshot.treatment_value == "treated"
    assert snapshot.control_value == "control"
    assert snapshot.intervention_date == "2025-02-01"


def test_synthetic_control_preserves_treated_unit_and_canonical_donor_pool() -> None:
    estimator_type = AnalysisEstimatorType.SYNTHETIC_CONTROL

    snapshot = TreatmentControlSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={"treated_unit": "Boston", "donor_pool": ["Seattle", "Austin"]},
        semantic_mapping=_mapping(),
        analysis_period=_period(estimator_type),
        analysis_selection=_selection(estimator_type),
    )

    assert snapshot.treated_units == ("Boston",)
    assert snapshot.control_units == ("Austin", "Seattle")


def test_geo_holdout_preserves_canonical_treated_and_control_geographies() -> None:
    estimator_type = AnalysisEstimatorType.GEO_HOLDOUT

    snapshot = TreatmentControlSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={
            "treated_geographies": ["Boston", "Miami"],
            "control_geographies": ["Seattle", "Austin"],
        },
        semantic_mapping=_mapping(),
        analysis_period=_period(estimator_type),
        analysis_selection=_selection(estimator_type),
    )

    assert snapshot.treated_units == ("Boston", "Miami")
    assert snapshot.control_units == ("Austin", "Seattle")


def test_off_policy_preserves_policy_and_propensity_assignment() -> None:
    estimator_type = AnalysisEstimatorType.OFF_POLICY_EVALUATION
    period = AnalysisPeriodSnapshot.from_configuration(
        estimator_type,
        {"analysis_start_date": "2025-01-01", "analysis_end_date": "2025-03-31"},
    )

    snapshot = TreatmentControlSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={
            "policy_name": "growth_policy",
            "behavior_propensity_column": "behavior_probability",
            "target_propensity_column": "target_probability",
        },
        semantic_mapping=_mapping(),
        analysis_period=period,
        analysis_selection=_selection(estimator_type),
    )

    assert snapshot.assignment_rule == "logged_policy_propensity"
    assert snapshot.policy_name == "growth_policy"
    assert snapshot.behavior_propensity_column == "behavior_probability"
    assert snapshot.target_propensity_column == "target_probability"


@pytest.mark.parametrize(
    ("estimator_type", "configuration"),
    [
        (
            AnalysisEstimatorType.SYNTHETIC_CONTROL,
            {"treated_unit": "Boston", "donor_pool": ["Boston", "Austin"]},
        ),
        (
            AnalysisEstimatorType.GEO_HOLDOUT,
            {
                "treated_geographies": ["Boston"],
                "control_geographies": ["Boston"],
            },
        ),
    ],
)
def test_treated_and_control_units_must_not_overlap(
    estimator_type: AnalysisEstimatorType, configuration: dict[str, object]
) -> None:
    with pytest.raises(InvalidAnalysisRunError, match="both treated and control"):
        TreatmentControlSnapshot.from_configuration(
            estimator_type=estimator_type,
            configuration=configuration,
            semantic_mapping=_mapping(),
            analysis_period=_period(estimator_type),
            analysis_selection=_selection(estimator_type),
        )


def test_canonical_json_round_trip_preserves_exact_definition() -> None:
    estimator_type = AnalysisEstimatorType.GEO_HOLDOUT
    snapshot = TreatmentControlSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={
            "treated_geographies": ["Miami", "Boston"],
            "control_geographies": ["Seattle", "Austin"],
            "excluded_control_units": ["Portland"],
            "control_eligibility_rules": [
                {
                    "column": "population",
                    "operator": "greater_than",
                    "value": {"type": "number", "value": 1000},
                }
            ],
        },
        semantic_mapping=_mapping(),
        analysis_period=_period(estimator_type),
        analysis_selection=_selection(estimator_type),
    )

    assert TreatmentControlSnapshot.from_json(snapshot.canonical_json) == snapshot


@pytest.mark.parametrize(
    "configuration",
    [
        {"treated_unit": "Boston", "donor_pool": []},
        {"treated_unit": " ", "donor_pool": ["Austin", "Seattle"]},
        {"treated_unit": "Boston", "donor_pool": ["Austin", "Austin"]},
    ],
)
def test_synthetic_control_rejects_incomplete_or_malformed_assignment(
    configuration: dict[str, object],
) -> None:
    estimator_type = AnalysisEstimatorType.SYNTHETIC_CONTROL

    with pytest.raises(InvalidAnalysisRunError):
        TreatmentControlSnapshot.from_configuration(
            estimator_type=estimator_type,
            configuration=configuration,
            semantic_mapping=_mapping(),
            analysis_period=_period(estimator_type),
            analysis_selection=_selection(estimator_type),
        )


def test_mmm_rejects_irrelevant_treatment_fields() -> None:
    estimator_type = AnalysisEstimatorType.MARKETING_MIX_MODEL
    period = AnalysisPeriodSnapshot.from_configuration(
        estimator_type,
        {"analysis_start_date": "2025-01-01", "analysis_end_date": "2025-03-31"},
    )

    with pytest.raises(InvalidAnalysisRunError, match="does not use"):
        TreatmentControlSnapshot.from_configuration(
            estimator_type=estimator_type,
            configuration={"treated_geographies": ["Boston"]},
            semantic_mapping=_mapping(),
            analysis_period=period,
            analysis_selection=_selection(estimator_type),
        )


def test_control_rule_rejects_unknown_column() -> None:
    estimator_type = AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES

    with pytest.raises(InvalidAnalysisRunError, match="unknown column"):
        TreatmentControlSnapshot.from_configuration(
            estimator_type=estimator_type,
            configuration={
                "control_eligibility_rules": [
                    {
                        "column": "not_in_dataset",
                        "operator": "equals",
                        "value": {"type": "string", "value": "yes"},
                    }
                ]
            },
            semantic_mapping=_mapping(),
            analysis_period=_period(estimator_type),
            analysis_selection=_selection(estimator_type),
        )


def test_explicit_assignment_must_be_available_in_analysis_selection() -> None:
    estimator_type = AnalysisEstimatorType.GEO_HOLDOUT
    selection = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={"selected_geographies": ["Boston", "Austin"]},
        semantic_mapping=_mapping(),
    )

    with pytest.raises(InvalidAnalysisRunError, match="outside the analysis selection"):
        TreatmentControlSnapshot.from_configuration(
            estimator_type=estimator_type,
            configuration={
                "treated_geographies": ["Miami"],
                "control_geographies": ["Austin"],
            },
            semantic_mapping=_mapping(),
            analysis_period=_period(estimator_type),
            analysis_selection=selection,
        )


def test_persisted_not_applicable_snapshot_rejects_assignment_values() -> None:
    values = TreatmentControlSnapshot.not_applicable().as_dict()
    values["treated_units"] = ["Boston"]

    with pytest.raises(InvalidAnalysisRunError, match="not-applicable"):
        TreatmentControlSnapshot.from_json(json.dumps(values))


def test_persisted_mapped_assignment_rejects_equal_treatment_and_control_values() -> None:
    estimator_type = AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES
    values = TreatmentControlSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={},
        semantic_mapping=_mapping(),
        analysis_period=_period(estimator_type),
        analysis_selection=_selection(estimator_type),
    ).as_dict()
    values["control_value"] = values["treatment_value"]

    with pytest.raises(InvalidAnalysisRunError, match="distinct"):
        TreatmentControlSnapshot.from_json(json.dumps(values))
