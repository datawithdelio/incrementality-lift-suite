import pytest

from incrementality_api.application.analysis_execution.estimation import (
    PermanentEstimationError,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.infrastructure.analysis_execution.selection import (
    AnalysisSelectionRowExecutor,
)


def test_executes_persisted_typed_selection_rules() -> None:
    mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="yes",
        control_value="no",
    )
    snapshot = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.GEO_HOLDOUT,
        semantic_mapping=mapping,
        configuration={
            "row_filters": [
                {
                    "column": "revenue",
                    "operator": "greater_than_or_equal",
                    "value": {"type": "number", "value": 100},
                },
                {
                    "column": "campaign",
                    "operator": "contains",
                    "value": {"type": "string", "value": "brand"},
                },
            ],
            "included_values": {"eligible": [{"type": "boolean", "value": True}]},
            "excluded_values": {"segment": [{"type": "string", "value": "Internal"}]},
            "selected_geographies": ["Boston"],
            "segment_column": "segment",
            "selected_segments": ["Enterprise"],
        },
    )
    rows = (
        {
            "market": "Boston",
            "revenue": "120",
            "campaign": "Brand Search",
            "eligible": "yes",
            "segment": "Enterprise",
        },
        {
            "market": "Boston",
            "revenue": "90",
            "campaign": "Brand Search",
            "eligible": "yes",
            "segment": "Enterprise",
        },
        {
            "market": "New York",
            "revenue": "120",
            "campaign": "Brand Search",
            "eligible": "yes",
            "segment": "Enterprise",
        },
        {
            "market": "Boston",
            "revenue": "120",
            "campaign": "Brand Search",
            "eligible": "yes",
            "segment": "Internal",
        },
    )

    assert AnalysisSelectionRowExecutor().filter(rows=rows, snapshot=snapshot) == rows[:1]


def test_mutating_source_configuration_after_queueing_does_not_change_selection() -> None:
    mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="yes",
        control_value="no",
    )
    mutable_configuration = {"selected_geographies": ["Boston"]}
    snapshot = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.GEO_HOLDOUT,
        semantic_mapping=mapping,
        configuration=mutable_configuration,
    )
    mutable_configuration["selected_geographies"] = ["New York"]
    rows = ({"market": "Boston"}, {"market": "New York"})

    assert AnalysisSelectionRowExecutor().filter(rows=rows, snapshot=snapshot) == rows[:1]


def test_rejects_selection_rules_targeting_unavailable_columns() -> None:
    mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="yes",
        control_value="no",
    )
    snapshot = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        semantic_mapping=mapping,
        configuration={
            "row_filters": [{"column": "missing", "operator": "is_null"}]
        },
    )

    with pytest.raises(PermanentEstimationError, match="unavailable column 'missing'"):
        AnalysisSelectionRowExecutor().filter(
            rows=({"market": "Boston"},), snapshot=snapshot
        )
