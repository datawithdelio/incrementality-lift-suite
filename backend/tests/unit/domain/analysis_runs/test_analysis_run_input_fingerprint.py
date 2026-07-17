import re
from datetime import UTC, datetime
from uuid import UUID

import pytest

from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")
DATASET_ID = UUID("33333333-3333-3333-3333-333333333333")
SEMANTIC_MAPPING_ID = UUID("44444444-4444-4444-4444-444444444444")
USER_ID = UUID("55555555-5555-5555-5555-555555555555")


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
    random_seed: int = 1_729,
) -> AnalysisRun:
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
        created_by_user_id=USER_ID,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        application_version="0.1.0",
        source_revision="a" * 40,
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
        created_by_user_id=USER_ID,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        application_version="0.2.0",
        source_revision="a" * 40,
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
        created_by_user_id=USER_ID,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        application_version="0.1.0",
        source_revision="b" * 40,
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
