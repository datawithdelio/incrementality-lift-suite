from datetime import UTC, datetime
from uuid import uuid4

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
from incrementality_api.infrastructure.database.repositories.analysis_runs import (
    to_analysis_run,
    to_analysis_run_model,
)


def test_analysis_run_repository_preserves_dataset_lineage() -> None:
    mapping_snapshot = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column="spend",
        covariate_columns=("promotion", "temperature"),
        treatment_value="yes",
        control_value="no",
    )
    run = AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256="a" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=3,
        semantic_mapping_snapshot=mapping_snapshot,
        analysis_period_snapshot=AnalysisPeriodSnapshot.from_configuration(
            AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
            {
                "analysis_start_date": "2026-01-01",
                "analysis_end_date": "2026-01-31",
                "intervention_date": "2026-01-15",
            },
        ),
        analysis_selection_snapshot=AnalysisSelectionSnapshot.from_configuration(
            estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
            semantic_mapping=mapping_snapshot,
            configuration={"selected_geographies": ["Boston", "New York"]},
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
    assert model.analysis_period_snapshot_json == (
        '{"analysis_end_date":"2026-01-31","analysis_start_date":"2026-01-01",'
        '"estimator_type":"difference_in_differences","intervention_date":"2026-01-15",'
        '"post_period_end_date":"2026-01-31","post_period_start_date":"2026-01-15",'
        '"pre_period_end_date":"2026-01-14","pre_period_start_date":"2026-01-01",'
        '"validation_end_date":null,"validation_start_date":null}'
    )
    assert model.analysis_selection_snapshot_json == (
        '{"eligibility_filters":[],"excluded_geographies":[],'
        '"excluded_segments":[],"excluded_values":{},"geography_column":"market",'
        '"included_values":{},"row_filters":[],"segment_column":null,'
        '"selected_geographies":["Boston","New York"],"selected_segments":[]}'
    )
    assert model.random_seed == run.random_seed
    assert model.input_fingerprint_sha256 == run.input_fingerprint_sha256

    reconstructed = to_analysis_run(model)

    assert reconstructed == run


def test_analysis_run_repository_restores_nullable_runtime_lineage_for_historical_rows() -> None:
    mapping_snapshot = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="yes",
        control_value="no",
    )
    run = AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256="a" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=3,
        semantic_mapping_snapshot=mapping_snapshot,
        analysis_period_snapshot=AnalysisPeriodSnapshot.from_configuration(
            AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
            {
                "analysis_start_date": "2026-01-01",
                "analysis_end_date": "2026-01-31",
                "intervention_date": "2026-01-15",
            },
        ),
        analysis_selection_snapshot=AnalysisSelectionSnapshot.from_configuration(
            estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
            configuration={},
            semantic_mapping=mapping_snapshot,
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
    historical_model.analysis_period_snapshot_json = None
    historical_model.analysis_selection_snapshot_json = None

    restored = to_analysis_run(historical_model)

    assert restored.application_version is None
    assert restored.source_revision is None
    assert restored.statistical_library_versions is None
    assert restored.semantic_mapping_snapshot is None
    assert restored.analysis_period_snapshot is None
    assert restored.analysis_selection_snapshot is None
