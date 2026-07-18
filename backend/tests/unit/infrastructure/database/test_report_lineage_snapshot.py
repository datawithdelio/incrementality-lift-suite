from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from incrementality_api.infrastructure.database.repositories.data_products import (
    _report_lineage_snapshot,
)


def test_report_lineage_snapshot_uses_persisted_analysis_run_values() -> None:
    run_id = uuid4()
    dataset_id = uuid4()
    mapping_id = uuid4()

    run = cast(
        Any,
        SimpleNamespace(
            id=run_id,
            dataset_id=dataset_id,
            dataset_checksum_sha256="a" * 64,
            dataset_byte_size=4096,
            semantic_mapping_id=mapping_id,
            semantic_mapping_version=3,
            semantic_mapping_snapshot_json=(
                '{"outcome_column":"revenue","treatment_column":"treated"}'
            ),
            analysis_period_snapshot_json=(
                '{"analysis_start_date":"2026-01-01",'
                '"analysis_end_date":"2026-01-31"}'
            ),
            analysis_selection_snapshot_json=(
                '{"selected_geographies":["Boston"]}'
            ),
            treatment_control_snapshot_json=(
                '{"treated_units":["Boston"],"control_units":["Chicago"]}'
            ),
            estimand_snapshot_json=(
                '{"estimand_type":"average_differential_change",'
                '"target_outcome":"revenue"}'
            ),
            estimator_type="difference_in_differences",
            estimator_version="did-v2",
            random_seed=1729,
            application_version="0.1.0",
            source_revision="b" * 40,
            statistical_library_versions_json=(
                '{"numpy":"2.3.1","statsmodels":"0.14.5"}'
            ),
            input_fingerprint_sha256="c" * 64,
        ),
    )

    lineage = _report_lineage_snapshot(run)

    assert lineage == {
        "analysis_run_id": str(run_id),
        "dataset_id": str(dataset_id),
        "dataset_checksum_sha256": "a" * 64,
        "dataset_byte_size": 4096,
        "semantic_mapping_id": str(mapping_id),
        "semantic_mapping_version": 3,
        "semantic_mapping_snapshot": {
            "outcome_column": "revenue",
            "treatment_column": "treated",
        },
        "analysis_period_snapshot": {
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31",
        },
        "analysis_selection_snapshot": {
            "selected_geographies": ["Boston"],
        },
        "treatment_control_snapshot": {
            "treated_units": ["Boston"],
            "control_units": ["Chicago"],
        },
        "estimand_snapshot": {
            "estimand_type": "average_differential_change",
            "target_outcome": "revenue",
        },
        "estimator_type": "difference_in_differences",
        "estimator_version": "did-v2",
        "random_seed": 1729,
        "application_version": "0.1.0",
        "source_revision": "b" * 40,
        "statistical_library_versions": {
            "numpy": "2.3.1",
            "statsmodels": "0.14.5",
        },
        "input_fingerprint_sha256": "c" * 64,
    }
