from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.estimand_snapshot import (
    EstimandSnapshot,
)
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
)
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)


def test_off_policy_estimand_targets_configured_reward_column() -> None:
    estimator_type = (
        AnalysisEstimatorType.OFF_POLICY_EVALUATION
    )

    mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="user_id",
        treatment_column="action",
        outcome_column="legacy_outcome",
        spend_column=None,
        covariate_columns=(),
        treatment_value="treated",
        control_value="control",
    )

    period = AnalysisPeriodSnapshot.from_configuration(
        estimator_type,
        {
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31",
        },
    )

    selection = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=estimator_type,
        configuration={},
        semantic_mapping=mapping,
    )

    treatment_control = (
        TreatmentControlSnapshot.from_configuration(
            estimator_type=estimator_type,
            configuration={
                "policy_name": "growth_policy",
                "behavior_propensity_column": (
                    "behavior_probability"
                ),
                "target_propensity_column": (
                    "target_probability"
                ),
            },
            semantic_mapping=mapping,
            analysis_period=period,
            analysis_selection=selection,
        )
    )

    snapshot = (
        EstimandSnapshot.from_validated_run_configuration(
            estimator_type=estimator_type,
            semantic_mapping=mapping,
            analysis_period=period,
            analysis_selection=selection,
            treatment_control=treatment_control,
            serialized=(
                "{"
                '"reward_column":"reward",'
                '"observed_action_expected_reward_column":"observed_expected_reward",'
            '"target_policy_expected_reward_column":"target_expected_reward",'
                '"primary_method":"doubly_robust"'
                "}"
            ),
        )
    )

    assert snapshot.target_outcome == "reward"
    assert snapshot.policy_target == "growth_policy"
    assert (
        snapshot.aggregation_method
        == "doubly_robust_mean_policy_value"
    )
