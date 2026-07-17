from datetime import UTC, datetime
from uuid import uuid4

from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.infrastructure.database.repositories.analysis_runs import (
    to_analysis_run,
    to_analysis_run_model,
)


def test_analysis_run_repository_preserves_dataset_lineage() -> None:
    run = AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256="a" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=3,
        semantic_mapping_snapshot=SemanticMappingSnapshot.create(
            time_column="date",
            unit_column="market",
            treatment_column="treated",
            outcome_column="revenue",
            spend_column="spend",
            covariate_columns=("promotion", "temperature"),
            treatment_value="yes",
            control_value="no",
        ),
        created_by_user_id=uuid4(),
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        estimator_version="did-v1",
        application_version="0.1.0",
        source_revision="a" * 40,
        statistical_library_versions={
            "numpy": "2.3.1",
            "statsmodels": "0.14.5",
        },
        random_seed=1_729,
        configuration_json='{"alpha":0.05}',
        created_at=datetime(2026, 7, 16, 18, 30, tzinfo=UTC),
    )

    model = to_analysis_run_model(run)

    assert model.dataset_checksum_sha256 == run.dataset_checksum_sha256
    assert model.dataset_byte_size == run.dataset_byte_size
    assert model.application_version == run.application_version
    assert model.source_revision == run.source_revision
    assert model.statistical_library_versions_json == (
        '{"numpy":"2.3.1","statsmodels":"0.14.5"}'
    )
    assert model.semantic_mapping_snapshot_json == (
        '{"control_value":"no","covariate_columns":["promotion","temperature"],'
        '"outcome_column":"revenue","spend_column":"spend","time_column":"date",'
        '"treatment_column":"treated","treatment_value":"yes","unit_column":"market"}'
    )
    assert model.random_seed == run.random_seed
    assert model.input_fingerprint_sha256 == run.input_fingerprint_sha256

    reconstructed = to_analysis_run(model)

    assert reconstructed == run


def test_analysis_run_repository_restores_nullable_runtime_lineage_for_historical_rows() -> None:
    run = AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256="a" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=3,
        semantic_mapping_snapshot=SemanticMappingSnapshot.create(
            time_column="date",
            unit_column="market",
            treatment_column="treated",
            outcome_column="revenue",
            spend_column=None,
            covariate_columns=(),
            treatment_value="yes",
            control_value="no",
        ),
        created_by_user_id=uuid4(),
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        estimator_version="did-v1",
        application_version="0.1.0",
        source_revision="a" * 40,
        statistical_library_versions={
            "numpy": "2.3.1",
            "statsmodels": "0.14.5",
        },
        random_seed=1_729,
        configuration_json='{"alpha":0.05}',
        created_at=datetime(2026, 7, 16, 18, 30, tzinfo=UTC),
    )
    historical_model = to_analysis_run_model(run)
    historical_model.application_version = None
    historical_model.source_revision = None
    historical_model.statistical_library_versions_json = None
    historical_model.semantic_mapping_snapshot_json = None

    restored = to_analysis_run(historical_model)

    assert restored.application_version is None
    assert restored.source_revision is None
    assert restored.statistical_library_versions is None
    assert restored.semantic_mapping_snapshot is None
