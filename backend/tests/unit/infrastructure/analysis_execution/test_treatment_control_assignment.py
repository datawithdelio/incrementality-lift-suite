import pytest

from incrementality_api.application.analysis_execution.estimation import (
    PermanentEstimationError,
)
from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)
from incrementality_api.infrastructure.analysis_execution.treatment_control import (
    TreatmentControlRowExecutor,
)


def _mapping() -> SemanticMappingSnapshot:
    return SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="variant",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=("population",),
        treatment_value="treated",
        control_value="control",
    )


def _snapshot() -> TreatmentControlSnapshot:
    mapping = _mapping()
    estimator_type = AnalysisEstimatorType.GEO_HOLDOUT
    period = AnalysisPeriodSnapshot.from_configuration(
        estimator_type,
        {
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31",
            "intervention_date": "2026-01-15",
        },
    )
    selection = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={},
        semantic_mapping=mapping,
    )
    return TreatmentControlSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={
            "treated_geographies": ["south"],
            "control_geographies": ["north"],
        },
        semantic_mapping=mapping,
        analysis_period=period,
        analysis_selection=selection,
    )


def test_filters_rows_to_persisted_treated_and_control_units() -> None:
    rows = (
        {"date": "2026-01-01", "market": "north", "variant": "control"},
        {"date": "2026-01-01", "market": "south", "variant": "treated"},
        {"date": "2026-01-01", "market": "west", "variant": "control"},
    )

    selected = TreatmentControlRowExecutor().filter(
        rows=rows,
        mapping=_mapping(),
        snapshot=_snapshot(),
    )

    assert selected == rows[:2]


def test_rejects_unit_whose_mapped_assignment_disagrees_with_snapshot() -> None:
    rows = (
        {"date": "2026-01-01", "market": "south", "variant": "control"},
    )

    with pytest.raises(PermanentEstimationError, match="disagrees"):
        TreatmentControlRowExecutor().filter(
            rows=rows,
            mapping=_mapping(),
            snapshot=_snapshot(),
        )


def test_applies_persisted_treatment_cohort_and_control_eligibility_rules() -> None:
    mapping = _mapping()
    estimator_type = AnalysisEstimatorType.GEO_HOLDOUT
    period = AnalysisPeriodSnapshot.from_configuration(
        estimator_type,
        {
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31",
            "intervention_date": "2026-01-15",
        },
    )
    selection = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={},
        semantic_mapping=mapping,
    )
    snapshot = TreatmentControlSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={
            "treated_geographies": ["south"],
            "control_geographies": ["north"],
            "treatment_cohort": [
                {
                    "column": "population",
                    "operator": "greater_than",
                    "value": {"type": "number", "value": 1000},
                }
            ],
            "control_eligibility_rules": [
                {
                    "column": "population",
                    "operator": "greater_than",
                    "value": {"type": "number", "value": 500},
                }
            ],
        },
        semantic_mapping=mapping,
        analysis_period=period,
        analysis_selection=selection,
    )
    rows = (
        {"market": "south", "variant": "treated", "population": "2000"},
        {"market": "south", "variant": "treated", "population": "500"},
        {"market": "north", "variant": "control", "population": "700"},
        {"market": "north", "variant": "control", "population": "400"},
    )

    selected = TreatmentControlRowExecutor().filter(
        rows=rows,
        mapping=mapping,
        snapshot=snapshot,
    )

    assert selected == (rows[0], rows[2])
