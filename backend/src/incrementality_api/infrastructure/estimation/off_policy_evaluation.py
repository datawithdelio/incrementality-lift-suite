"""Off-policy evaluation with custom reliability policy and trusted numeric routines."""

import numpy as np
from scipy import stats  # type: ignore[import-untyped]

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
    OffPolicyEvaluationInput,
    PermanentEstimationError,
)
from incrementality_api.infrastructure.estimation.package_versions import (
    installed_distribution_version,
)

_METHODS = {
    "importance_sampling",
    "self_normalized_importance_sampling",
    "doubly_robust",
}


class StatsmodelsOffPolicyEstimator:
    """Estimate logged-policy value while keeping reliability rules explicit."""

    statistical_packages = ("numpy", "scipy")

    def estimate(
        self,
        estimator_input: object,
        *,
        random_seed: int,
    ) -> AnalysisEstimationResult:
        del random_seed

        if not isinstance(estimator_input, OffPolicyEvaluationInput):
            raise PermanentEstimationError("Off-policy estimator input is invalid.")
        if estimator_input.primary_method not in _METHODS:
            raise PermanentEstimationError(
                f"Unsupported off-policy method '{estimator_input.primary_method}'."
            )
        rewards = np.asarray([item.reward for item in estimator_input.observations])
        behavior = np.asarray([item.behavior_probability for item in estimator_input.observations])
        target = np.asarray([item.target_probability for item in estimator_input.observations])
        observed_action_predictions = np.asarray(
            [
                item.observed_action_expected_reward
                for item in estimator_input.observations
            ]
        )
        target_policy_predictions = np.asarray(
            [
                item.target_policy_expected_reward
                for item in estimator_input.observations
            ]
        )
        if (
            rewards.size < 2
            or not np.all(np.isfinite(rewards))
            or not np.all(np.isfinite(observed_action_predictions))
        or not np.all(np.isfinite(target_policy_predictions))
            or np.any(behavior <= 0)
            or np.any(behavior > 1)
            or np.any(target < 0)
            or np.any(target > 1)
        ):
            raise PermanentEstimationError("Policy propensities or rewards are invalid.")

        weights = target / behavior
        weight_sum = float(weights.sum())
        if weight_sum <= 0:
            raise PermanentEstimationError("Target policy has no propensity overlap.")
        influence = {
            "importance_sampling": weights * rewards,
            "self_normalized_importance_sampling": (weights * rewards * rewards.size / weight_sum),
            "doubly_robust": (
                target_policy_predictions
                + weights * (rewards - observed_action_predictions)
            ),
        }
        estimates = {name: float(values.mean()) for name, values in influence.items()}
        selected = influence[estimator_input.primary_method]
        estimate = estimates[estimator_input.primary_method]
        standard_error = float(selected.std(ddof=1) / np.sqrt(selected.size))
        critical = float(stats.norm.ppf(0.975))
        low = estimate - critical * standard_error
        high = estimate + critical * standard_error
        effective_sample_size = float(weight_sum**2 / np.square(weights).sum())
        extreme_count = int(np.sum(weights > 10))
        weak = (
            effective_sample_size < rewards.size * 0.5
            or extreme_count > 0
            or float(behavior.min()) < 0.05
        )
        warning = (
            "Weak propensity overlap creates extreme weights; treat this comparison as directional."
            if weak
            else "Historical decisions provide strong overlap for this policy comparison."
        )
        z_score = estimate / standard_error if standard_error > 0 else 0.0
        return AnalysisEstimationResult(
            effect=estimate,
            standard_error=standard_error,
            p_value=float(2 * stats.norm.sf(abs(z_score))),
            confidence_interval_low=low,
            confidence_interval_high=high,
            observation_count=int(rewards.size),
            library_name="numpy-scipy",
            library_version=(
                f"numpy {installed_distribution_version('numpy')}; "
                f"scipy {installed_distribution_version('scipy')}"
            ),
            diagnostics={
                "policy_name": estimator_input.policy_name,
                "primary_method": estimator_input.primary_method,
                "policy_estimates": estimates,
                "effective_sample_size": effective_sample_size,
                "propensity_overlap": {
                    "minimum_behavior_propensity": float(behavior.min()),
                    "maximum_importance_weight": float(weights.max()),
                    "zero_target_share": float(np.mean(target == 0)),
                },
                "extreme_weight_count": extreme_count,
                "reliability": "weak" if weak else "strong",
                "design_assessment": "weak" if weak else "valid",
                "causal_claim_allowed": False,
                "recommendations_allowed": not weak,
                "plain_language_warning": warning,
                "policy_comparison": [
                    {"method": name, "estimated_policy_value": value}
                    for name, value in estimates.items()
                ],
            },
        )
