import re
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

import pytest

from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")
DATASET_ID = UUID("33333333-3333-3333-3333-333333333333")
SEMANTIC_MAPPING_ID = UUID("44444444-4444-4444-4444-444444444444")
USER_ID = UUID("55555555-5555-5555-5555-555555555555")
MAPPING_SNAPSHOT: dict[str, object] = {
    "time_column": "date",
    "unit_column": "market",
    "treatment_column": "treated",
    "outcome_column": "revenue",
    "spend_column": "spend",
    "covariate_columns": ["promotion", "temperature"],
    "treatment_value": "yes",
    "control_value": "no",
}
PERIOD_SNAPSHOT = AnalysisPeriodSnapshot.from_configuration(
    AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
    {
        "analysis_start_date": "2026-01-01",
        "analysis_end_date": "2026-01-31",
        "intervention_date": "2026-01-15",
    },
)
SELECTION_SNAPSHOT = AnalysisSelectionSnapshot.from_configuration(
    estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
    configuration={},
    semantic_mapping=SemanticMappingSnapshot.from_mapping(MAPPING_SNAPSHOT),
)


def queue_run(
    *,
    configuration_json: str = ('{"alpha":0.05,"include_unit_fixed_effects":true}'),
    created_at: datetime = datetime(
        2026,
        7,
        16,
        12,
        0,
        tzinfo=UTC,
    ),
    dataset_checksum_sha256: str = "a" * 64,
    dataset_byte_size: int = 4_096,
    semantic_mapping_id: UUID = SEMANTIC_MAPPING_ID,
    semantic_mapping_version: int = 3,
    estimator_type: AnalysisEstimatorType = (AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
    estimator_version: str = "did-v1",
    application_version: str = "0.1.0",
    source_revision: str = "a" * 40,
    statistical_library_versions: Mapping[str, str] | None = None,
    semantic_mapping_snapshot: Mapping[str, object] | None = None,
    random_seed: int = 1_729,
    analysis_period_snapshot: AnalysisPeriodSnapshot | None = None,
    analysis_selection_snapshot: AnalysisSelectionSnapshot | None = None,
) -> AnalysisRun:
    mapping_snapshot = SemanticMappingSnapshot.from_mapping(
        semantic_mapping_snapshot or MAPPING_SNAPSHOT
    )
    return AnalysisRun.queue(
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        dataset_checksum_sha256=dataset_checksum_sha256,
        dataset_byte_size=dataset_byte_size,
        semantic_mapping_id=semantic_mapping_id,
        semantic_mapping_version=semantic_mapping_version,
        created_by_user_id=USER_ID,
        estimator_type=estimator_type,
        estimator_version=estimator_version,
        application_version=application_version,
        source_revision=source_revision,
        statistical_library_versions=(
            statistical_library_versions
            or {
                "numpy": "2.3.1",
                "statsmodels": "0.14.5",
            }
        ),
        semantic_mapping_snapshot=mapping_snapshot,
        analysis_period_snapshot=(
            analysis_period_snapshot
            or AnalysisPeriodSnapshot.from_configuration(
                estimator_type,
                {
                    "analysis_start_date": "2026-01-01",
                    "analysis_end_date": "2026-01-31",
                    **(
                        {"intervention_date": "2026-01-15"}
                        if estimator_type
                        in {
                            AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
                            AnalysisEstimatorType.SYNTHETIC_CONTROL,
                            AnalysisEstimatorType.GEO_HOLDOUT,
                        }
                        else {}
                    ),
                },
            )
        ),
        analysis_selection_snapshot=(
            analysis_selection_snapshot
            or AnalysisSelectionSnapshot.from_configuration(
                estimator_type=estimator_type,
                configuration={},
                semantic_mapping=mapping_snapshot,
            )
        ),
        random_seed=random_seed,
        configuration_json=configuration_json,
        created_at=created_at,
    )


def test_identical_inputs_produce_same_deterministic_fingerprint() -> None:
    first = queue_run(
        configuration_json="""
        {
          "alpha": 0.05,
          "include_unit_fixed_effects": true
        }
        """,
        created_at=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
    )

    second = queue_run(
        configuration_json=('{"include_unit_fixed_effects":true,"alpha":0.05}'),
        created_at=datetime(2026, 7, 16, 12, 5, tzinfo=UTC),
    )

    assert first.id != second.id
    assert first.configuration_json == second.configuration_json
    assert first.input_fingerprint_sha256 == second.input_fingerprint_sha256
    assert re.fullmatch(
        r"[0-9a-f]{64}",
        first.input_fingerprint_sha256,
    )


@pytest.mark.parametrize(
    ("changed_argument", "changed_value"),
    [
        ("dataset_checksum_sha256", "b" * 64),
        ("dataset_byte_size", 8_192),
        (
            "semantic_mapping_id",
            UUID("66666666-6666-6666-6666-666666666666"),
        ),
        ("semantic_mapping_version", 4),
        (
            "estimator_type",
            AnalysisEstimatorType.SYNTHETIC_CONTROL,
        ),
        ("estimator_version", "did-v2"),
        ("random_seed", 9_999),
        (
            "configuration_json",
            ('{"alpha":0.10,"include_unit_fixed_effects":true}'),
        ),
    ],
)
def test_each_estimation_input_changes_the_fingerprint(
    changed_argument: str,
    changed_value: object,
) -> None:
    baseline = queue_run()

    changed = queue_run(
        **{
            changed_argument: changed_value,
        }
    )

    assert changed.input_fingerprint_sha256 != baseline.input_fingerprint_sha256


def test_runtime_versions_are_snapshotted_and_fingerprinted() -> None:
    baseline = AnalysisRun.queue(
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        dataset_checksum_sha256="a" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=SEMANTIC_MAPPING_ID,
        semantic_mapping_version=3,
        semantic_mapping_snapshot=SemanticMappingSnapshot.from_mapping(MAPPING_SNAPSHOT),
        analysis_period_snapshot=PERIOD_SNAPSHOT,
        analysis_selection_snapshot=SELECTION_SNAPSHOT,
        created_by_user_id=USER_ID,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        application_version="0.1.0",
        source_revision="a" * 40,
        statistical_library_versions={"numpy": "2.3.1", "statsmodels": "0.14.5"},
        random_seed=1_729,
        configuration_json=('{"alpha":0.05,"include_unit_fixed_effects":true}'),
        created_at=datetime(
            2026,
            7,
            16,
            12,
            0,
            tzinfo=UTC,
        ),
    )

    changed_application = AnalysisRun.queue(
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        dataset_checksum_sha256="a" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=SEMANTIC_MAPPING_ID,
        semantic_mapping_version=3,
        semantic_mapping_snapshot=SemanticMappingSnapshot.from_mapping(MAPPING_SNAPSHOT),
        analysis_period_snapshot=PERIOD_SNAPSHOT,
        analysis_selection_snapshot=SELECTION_SNAPSHOT,
        created_by_user_id=USER_ID,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        application_version="0.2.0",
        source_revision="a" * 40,
        statistical_library_versions={"numpy": "2.3.1", "statsmodels": "0.14.5"},
        random_seed=1_729,
        configuration_json=('{"alpha":0.05,"include_unit_fixed_effects":true}'),
        created_at=datetime(
            2026,
            7,
            16,
            12,
            0,
            tzinfo=UTC,
        ),
    )

    changed_source = AnalysisRun.queue(
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        dataset_checksum_sha256="a" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=SEMANTIC_MAPPING_ID,
        semantic_mapping_version=3,
        semantic_mapping_snapshot=SemanticMappingSnapshot.from_mapping(MAPPING_SNAPSHOT),
        analysis_period_snapshot=PERIOD_SNAPSHOT,
        analysis_selection_snapshot=SELECTION_SNAPSHOT,
        created_by_user_id=USER_ID,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        application_version="0.1.0",
        source_revision="b" * 40,
        statistical_library_versions={"numpy": "2.3.1", "statsmodels": "0.14.5"},
        random_seed=1_729,
        configuration_json=('{"alpha":0.05,"include_unit_fixed_effects":true}'),
        created_at=datetime(
            2026,
            7,
            16,
            12,
            0,
            tzinfo=UTC,
        ),
    )

    assert baseline.application_version == "0.1.0"
    assert baseline.source_revision == "a" * 40

    assert changed_application.input_fingerprint_sha256 != baseline.input_fingerprint_sha256
    assert changed_source.input_fingerprint_sha256 != baseline.input_fingerprint_sha256


def test_statistical_library_mapping_order_does_not_change_fingerprint() -> None:
    first = queue_run(
        statistical_library_versions={
            "statsmodels": "0.14.5",
            "numpy": "2.3.1",
        }
    )
    second = queue_run(
        statistical_library_versions={
            "numpy": "2.3.1",
            "statsmodels": "0.14.5",
        }
    )

    assert first.statistical_library_versions == second.statistical_library_versions
    assert first.input_fingerprint_sha256 == second.input_fingerprint_sha256


def test_changing_statistical_library_version_changes_fingerprint() -> None:
    baseline = queue_run()
    changed = queue_run(
        statistical_library_versions={
            "numpy": "2.4.0",
            "statsmodels": "0.14.5",
        }
    )

    assert changed.input_fingerprint_sha256 != baseline.input_fingerprint_sha256


def test_equivalent_semantic_mapping_snapshots_produce_same_fingerprint() -> None:
    first = queue_run(
        semantic_mapping_snapshot={
            "time_column": "date",
            "unit_column": "market",
            "treatment_column": "treated",
            "outcome_column": "revenue",
            "spend_column": "spend",
            "covariate_columns": [" Promotion ", "TEMPERATURE"],
            "treatment_value": "yes",
            "control_value": "no",
        }
    )
    second = queue_run()

    assert first.semantic_mapping_snapshot == second.semantic_mapping_snapshot
    assert first.input_fingerprint_sha256 == second.input_fingerprint_sha256


@pytest.mark.parametrize(
    ("changed_field", "changed_value"),
    [
        ("time_column", "week"),
        ("unit_column", "region"),
        ("treatment_column", "exposed"),
        ("outcome_column", "conversions"),
        ("spend_column", None),
        ("covariate_columns", ["holiday"]),
        ("treatment_value", "1"),
        ("control_value", "0"),
    ],
)
def test_changing_each_semantic_mapping_value_changes_fingerprint(
    changed_field: str,
    changed_value: object,
) -> None:
    baseline_values: dict[str, object] = {
        "time_column": "date",
        "unit_column": "market",
        "treatment_column": "treated",
        "outcome_column": "revenue",
        "spend_column": "spend",
        "covariate_columns": ["promotion", "temperature"],
        "treatment_value": "yes",
        "control_value": "no",
    }
    changed_values = {**baseline_values, changed_field: changed_value}

    assert (
        queue_run(semantic_mapping_snapshot=changed_values).input_fingerprint_sha256
        != queue_run().input_fingerprint_sha256
    )


def test_equivalent_analysis_period_representations_produce_same_fingerprint() -> None:
    date_snapshot = AnalysisPeriodSnapshot.from_configuration(
        AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        {
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31",
            "intervention_date": "2026-01-15",
        },
    )
    datetime_snapshot = AnalysisPeriodSnapshot.from_configuration(
        AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        {
            "analysis_start_date": "2026-01-01T00:00:00Z",
            "analysis_end_date": "2026-01-31T23:59:59+00:00",
            "intervention_date": "2026-01-15T12:00:00+00:00",
        },
    )

    assert (
        queue_run(analysis_period_snapshot=date_snapshot).input_fingerprint_sha256
        == queue_run(analysis_period_snapshot=datetime_snapshot).input_fingerprint_sha256
    )


@pytest.mark.parametrize(
    ("field_name", "changed_value"),
    [
        ("analysis_start_date", "2025-12-31"),
        ("analysis_end_date", "2026-02-01"),
        ("intervention_date", "2026-01-16"),
        ("pre_period_start_date", "2026-01-02"),
        ("pre_period_end_date", "2026-01-13"),
        ("post_period_start_date", "2026-01-16"),
        ("post_period_end_date", "2026-01-30"),
    ],
)
def test_changing_each_relevant_analysis_date_changes_fingerprint(
    field_name: str, changed_value: str
) -> None:
    values: dict[str, object] = {
        "analysis_start_date": "2026-01-01",
        "analysis_end_date": "2026-01-31",
        "intervention_date": "2026-01-15",
        "pre_period_start_date": "2026-01-01",
        "pre_period_end_date": "2026-01-14",
        "post_period_start_date": "2026-01-15",
        "post_period_end_date": "2026-01-31",
    }
    if field_name == "intervention_date":
        values["pre_period_end_date"] = "2026-01-15"
        values["post_period_start_date"] = "2026-01-16"
    changed = AnalysisPeriodSnapshot.from_configuration(
        AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        {**values, field_name: changed_value},
    )

    assert (
        queue_run(analysis_period_snapshot=changed).input_fingerprint_sha256
        != queue_run().input_fingerprint_sha256
    )


def test_equivalent_selection_ordering_produces_same_fingerprint() -> None:
    first = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        semantic_mapping=SemanticMappingSnapshot.from_mapping(MAPPING_SNAPSHOT),
        configuration={
            "included_values": {
                "channel": [
                    {"type": "string", "value": "Social"},
                    {"type": "string", "value": "Search"},
                ]
            }
        },
    )
    second = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        semantic_mapping=SemanticMappingSnapshot.from_mapping(MAPPING_SNAPSHOT),
        configuration={
            "included_values": {
                "channel": [
                    {"value": "Search", "type": "string"},
                    {"value": "Social", "type": "string"},
                ]
            }
        },
    )

    assert (
        queue_run(analysis_selection_snapshot=first).input_fingerprint_sha256
        == queue_run(analysis_selection_snapshot=second).input_fingerprint_sha256
    )


@pytest.mark.parametrize(
    "configuration",
    [
        {
            "row_filters": [
                {
                    "column": "revenue",
                    "operator": "greater_than",
                    "value": {"type": "number", "value": 100},
                }
            ]
        },
        {"included_values": {"channel": [{"type": "string", "value": "Search"}]}},
        {"excluded_values": {"channel": [{"type": "string", "value": "Internal"}]}},
        {"selected_geographies": ["Boston"]},
        {"excluded_geographies": ["Test Market"]},
        {"segment_column": "segment", "selected_segments": ["Enterprise"]},
        {"segment_column": "segment", "excluded_segments": ["Internal"]},
        {
            "eligibility_filters": [
                {
                    "column": "eligible",
                    "operator": "equals",
                    "value": {"type": "boolean", "value": True},
                }
            ]
        },
    ],
)
def test_changing_each_selection_criterion_changes_fingerprint(
    configuration: dict[str, object],
) -> None:
    changed = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        semantic_mapping=SemanticMappingSnapshot.from_mapping(MAPPING_SNAPSHOT),
        configuration=configuration,
    )

    assert (
        queue_run(analysis_selection_snapshot=changed).input_fingerprint_sha256
        != queue_run().input_fingerprint_sha256
    )
