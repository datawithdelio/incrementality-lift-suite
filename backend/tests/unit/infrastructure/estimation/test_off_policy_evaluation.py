import pytest

from incrementality_api.application.analysis_execution.estimation import (
    OffPolicyEvaluationInput,
    PermanentEstimationError,
    PolicyEvaluationObservation,
)
from incrementality_api.infrastructure.estimation.off_policy_evaluation import (
    StatsmodelsOffPolicyEstimator,
)


def policy_input(*, weak_overlap: bool = False) -> OffPolicyEvaluationInput:
    observations = tuple(
        PolicyEvaluationObservation(
            reward=float(2 + index % 3),
            behavior_probability=(0.001 if weak_overlap and index == 0 else 0.5),
            target_probability=(0.9 if weak_overlap and index == 0 else 0.6),
            expected_reward=float(2.2 + index % 3),
        )
        for index in range(40)
    )
    return OffPolicyEvaluationInput(
        observations=observations,
        policy_name="growth_policy",
        primary_method="doubly_robust",
    )


def test_strong_overlap_reports_all_estimators_and_effective_sample_size() -> None:
    result = StatsmodelsOffPolicyEstimator().estimate(policy_input(), random_seed=1_729)

    estimates = result.diagnostics["policy_estimates"]
    assert set(estimates) == {
        "importance_sampling",
        "self_normalized_importance_sampling",
        "doubly_robust",
    }
    assert result.diagnostics["reliability"] == "strong"
    assert result.diagnostics["effective_sample_size"] == pytest.approx(40.0)
    assert result.confidence_interval_low < result.effect < result.confidence_interval_high


def test_weak_overlap_warns_about_extreme_weights() -> None:
    result = StatsmodelsOffPolicyEstimator().estimate(
        policy_input(weak_overlap=True), random_seed=1_729
    )

    assert result.diagnostics["reliability"] == "weak"
    assert result.diagnostics["extreme_weight_count"] == 1
    assert result.diagnostics["causal_claim_allowed"] is False
    assert "overlap" in str(result.diagnostics["plain_language_warning"]).lower()


@pytest.mark.parametrize(
    ("behavior", "target"),
    [(0.0, 0.5), (-0.1, 0.5), (1.1, 0.5), (0.5, -0.1), (0.5, 1.1)],
)
def test_invalid_propensities_are_rejected(behavior: float, target: float) -> None:
    estimator_input = OffPolicyEvaluationInput(
        observations=(PolicyEvaluationObservation(1.0, behavior, target, 1.0),),
        policy_name="invalid",
    )

    with pytest.raises(PermanentEstimationError, match="propensit"):
        StatsmodelsOffPolicyEstimator().estimate(estimator_input, random_seed=1_729)


def test_unsupported_primary_method_is_rejected() -> None:
    estimator_input = OffPolicyEvaluationInput(
        observations=policy_input().observations,
        policy_name="growth_policy",
        primary_method="direct_method",
    )

    with pytest.raises(PermanentEstimationError, match="Unsupported off-policy method"):
        StatsmodelsOffPolicyEstimator().estimate(estimator_input, random_seed=1_729)

def test_identical_off_policy_inputs_produce_identical_results() -> None:
    estimator = StatsmodelsOffPolicyEstimator()
    estimator_input = policy_input()

    first = estimator.estimate(
        estimator_input,
        random_seed=1_729,
    )
    second = estimator.estimate(
        estimator_input,
        random_seed=1_729,
    )

    assert first == second
