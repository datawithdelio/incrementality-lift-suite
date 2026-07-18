from dataclasses import replace
from uuid import UUID

from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.estimand_snapshot import EstimandSnapshot
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.statistical_library_versions import (
    StatisticalLibraryVersions,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)


def test_input_fingerprint_changes_when_estimand_changes() -> None:
    estimator_type = AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES

    mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="true",
        control_value="false",
    )

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

    treatment_control = TreatmentControlSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={},
        semantic_mapping=mapping,
        analysis_period=period,
        analysis_selection=selection,
    )

    estimand = EstimandSnapshot.from_validated_run_configuration(
        estimator_type=estimator_type,
        semantic_mapping=mapping,
        analysis_period=period,
        analysis_selection=selection,
        treatment_control=treatment_control,
        serialized="{}",
    )

    changed_estimand = replace(
        estimand,
        estimand_type="different_meaningful_estimand",
    )

    common = {
        "dataset_checksum_sha256": "a" * 64,
        "dataset_byte_size": 4096,
        "semantic_mapping_id": UUID("00000000-0000-0000-0000-000000000001"),
        "semantic_mapping_version": 1,
        "semantic_mapping_snapshot": mapping,
        "analysis_period_snapshot": period,
        "analysis_selection_snapshot": selection,
        "treatment_control_snapshot": treatment_control,
        "estimator_type": estimator_type,
        "estimator_version": "did-v1",
        "application_version": "0.1.0",
        "source_revision": "b" * 40,
        "statistical_library_versions": StatisticalLibraryVersions.from_mapping(
            {
                "numpy": "2.3.1",
                "statsmodels": "0.14.5",
            }
        ),
        "random_seed": 1729,
        "configuration_json": "{}",
    }

    first = AnalysisRun._build_input_fingerprint_sha256(
        **common,
        estimand_snapshot=estimand,
    )
    second = AnalysisRun._build_input_fingerprint_sha256(
        **common,
        estimand_snapshot=changed_estimand,
    )

    assert first != second
