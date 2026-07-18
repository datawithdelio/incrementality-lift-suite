import json

import pytest

from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

MAPPING = SemanticMappingSnapshot.create(
    time_column="date",
    unit_column="market",
    treatment_column="treated",
    outcome_column="revenue",
    spend_column="spend",
    covariate_columns=("promotion",),
    treatment_value="yes",
    control_value="no",
)


@pytest.mark.parametrize("estimator_type", list(AnalysisEstimatorType))
def test_no_filter_analysis_has_a_canonical_empty_selection_snapshot(
    estimator_type: AnalysisEstimatorType,
) -> None:
    snapshot = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={},
        semantic_mapping=MAPPING,
    )

    assert snapshot.as_dict() == {
        "row_filters": [],
        "included_values": {},
        "excluded_values": {},
        "geography_column": None,
        "selected_geographies": [],
        "excluded_geographies": [],
        "segment_column": None,
        "selected_segments": [],
        "excluded_segments": [],
        "eligibility_filters": [],
    }


def test_exact_filters_exclusions_geographies_and_segments_are_snapshotted() -> None:
    snapshot = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.GEO_HOLDOUT,
        semantic_mapping=MAPPING,
        configuration={
            "row_filters": [
                {
                    "column": "revenue",
                    "operator": "greater_than",
                    "value": {"type": "number", "value": 100},
                },
                {
                    "column": "campaign",
                    "operator": "contains",
                    "value": {"type": "string", "value": "Brand"},
                },
            ],
            "included_values": {
                "channel": [
                    {"type": "string", "value": "Paid Search"},
                    {"type": "string", "value": "Social"},
                ]
            },
            "excluded_values": {"is_test": [{"type": "boolean", "value": True}]},
            "selected_geographies": ["New York", "Boston"],
            "excluded_geographies": ["Test Market"],
            "segment_column": "audience_segment",
            "selected_segments": ["Enterprise", "SMB"],
            "excluded_segments": ["Internal"],
            "eligibility_filters": [
                {
                    "column": "signup_date",
                    "operator": "less_than_or_equal",
                    "value": {"type": "date", "value": "2026-01-01"},
                }
            ],
        },
    )

    assert snapshot.as_dict() == {
        "row_filters": [
            {
                "column": "campaign",
                "operator": "contains",
                "value": {"type": "string", "value": "Brand"},
            },
            {
                "column": "revenue",
                "operator": "greater_than",
                "value": {"type": "number", "value": 100},
            },
        ],
        "included_values": {
            "channel": [
                {"type": "string", "value": "Paid Search"},
                {"type": "string", "value": "Social"},
            ]
        },
        "excluded_values": {"is_test": [{"type": "boolean", "value": True}]},
        "geography_column": "market",
        "selected_geographies": ["Boston", "New York"],
        "excluded_geographies": ["Test Market"],
        "segment_column": "audience_segment",
        "selected_segments": ["Enterprise", "SMB"],
        "excluded_segments": ["Internal"],
        "eligibility_filters": [
            {
                "column": "signup_date",
                "operator": "less_than_or_equal",
                "value": {"type": "date", "value": "2026-01-01"},
            }
        ],
    }


def test_equivalent_dictionary_and_collection_order_has_same_canonical_snapshot() -> None:
    first = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        semantic_mapping=MAPPING,
        configuration={
            "included_values": {
                "channel": [
                    {"type": "string", "value": "Social"},
                    {"type": "string", "value": "Search"},
                ],
                "country": [{"type": "string", "value": "US"}],
            },
            "selected_geographies": ["New York", "Boston"],
        },
    )
    second = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        semantic_mapping=MAPPING,
        configuration={
            "selected_geographies": ["Boston", "New York"],
            "included_values": {
                "country": [{"value": "US", "type": "string"}],
                "channel": [
                    {"value": "Search", "type": "string"},
                    {"value": "Social", "type": "string"},
                ],
            },
        },
    )

    assert first == second
    assert first.canonical_json == second.canonical_json


@pytest.mark.parametrize(
    ("configuration", "message"),
    [
        (
            {"included_values": {" ": [{"type": "string", "value": "US"}]}},
            "field name",
        ),
        (
            {"selected_geographies": ["US", " US "]},
            "duplicate",
        ),
        (
            {
                "selected_segments": ["Enterprise"],
                "excluded_segments": ["Enterprise"],
                "segment_column": "segment",
            },
            "included and excluded",
        ),
        (
            {
                "included_values": {"country": [{"type": "string", "value": "US"}]},
                "excluded_values": {"country": [{"type": "string", "value": "US"}]},
            },
            "included and excluded",
        ),
        (
            {
                "row_filters": [
                    {
                        "column": "revenue",
                        "operator": "approximately",
                        "value": {"type": "number", "value": 1},
                    }
                ]
            },
            "operator",
        ),
        (
            {
                "row_filters": [
                    {
                        "column": "revenue",
                        "operator": "contains",
                        "value": {"type": "number", "value": 1},
                    }
                ]
            },
            "string value",
        ),
        (
            {
                "row_filters": [
                    {
                        "column": "country",
                        "operator": "is_null",
                        "value": {"type": "string", "value": "US"},
                    }
                ]
            },
            "must not have a value",
        ),
        ({"selected_segments": ["SMB"]}, "segment_column"),
        ({"selected_geographies": [" "]}, "blank values"),
        (
            {"segment_column": "segment", "selected_segments": [" "]},
            "blank values",
        ),
    ],
)
def test_invalid_selection_criteria_are_rejected(
    configuration: dict[str, object], message: str
) -> None:
    with pytest.raises(InvalidAnalysisRunError, match=message):
        AnalysisSelectionSnapshot.from_configuration(
            estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
            configuration=configuration,
            semantic_mapping=MAPPING,
        )


def test_canonical_json_round_trips_and_rejects_malformed_roots() -> None:
    snapshot = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.GEO_HOLDOUT,
        semantic_mapping=MAPPING,
        configuration={"selected_geographies": ["Boston", "New York"]},
    )

    assert AnalysisSelectionSnapshot.from_json(snapshot.canonical_json) == snapshot
    with pytest.raises(InvalidAnalysisRunError, match="JSON object"):
        AnalysisSelectionSnapshot.from_json(json.dumps([]))
