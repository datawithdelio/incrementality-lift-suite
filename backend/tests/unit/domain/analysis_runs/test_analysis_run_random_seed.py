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
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
)

APPLICATION_VERSION = "0.1.0"
SOURCE_REVISION = "a" * 40


def test_analysis_run_records_random_seed() -> None:
    mapping_snapshot = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="true",
        control_value="false",
    )
    run = AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256="a" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=1,
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
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        random_seed=1_729,
        configuration_json='{"alpha":0.05}',
        created_at=datetime(
            2026,
            7,
            16,
            19,
            0,
            tzinfo=UTC,
        ),
        application_version=APPLICATION_VERSION,
        source_revision=SOURCE_REVISION,
        statistical_library_versions={"numpy": "2.3.1", "statsmodels": "0.14.5"},
    )

    assert run.random_seed == 1_729
