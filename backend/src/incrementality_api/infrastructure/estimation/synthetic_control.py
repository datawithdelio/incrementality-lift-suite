import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import scipy  # type: ignore[import-untyped]
from scipy.optimize import minimize  # type: ignore[import-untyped]

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
    PanelObservation,
    PermanentEstimationError,
    SyntheticControlInput,
)


@dataclass(frozen=True, slots=True)
class SyntheticControlFit:
    weights: np.ndarray
    predicted: np.ndarray
    pre_rmspe: float
    post_rmspe: float


class SyntheticControlDiagnosticPolicy:
    """Classify design quality without coupling policy to SciPy."""

    def assess(
        self, *, normalized_pre_rmspe: float, donor_count: int, placebo_p_value: float
    ) -> tuple[str, bool, list[str], str]:
        warnings: list[str] = []
        if normalized_pre_rmspe > 0.20:
            warnings.append("The donor pool cannot reproduce the target before treatment.")
            return (
                "invalid",
                False,
                warnings,
                "The pre-treatment fit is too weak to support a causal conclusion.",
            )
        if normalized_pre_rmspe > 0.10:
            warnings.append("Pre-treatment fit is weaker than recommended.")
        if donor_count < 3:
            warnings.append("Fewer than three donor units contribute to the synthetic control.")
        if placebo_p_value > 0.25:
            warnings.append("Placebo units show effects as large as the treated unit.")
        if warnings:
            return (
                "weak",
                False,
                warnings,
                "The estimated gap is directional, but the design needs stronger evidence.",
            )
        return (
            "valid",
            True,
            warnings,
            "The synthetic control supports a credible incremental effect after treatment.",
        )


class ScipySyntheticControlEstimator:
    """Thin constrained-weight adapter backed by SciPy SLSQP."""

    def __init__(self, policy: SyntheticControlDiagnosticPolicy | None = None) -> None:
        self._policy = policy or SyntheticControlDiagnosticPolicy()

    def estimate(
        self,
        estimator_input: object,
        *,
        random_seed: int,
    ) -> AnalysisEstimationResult:
        del random_seed

        if not isinstance(estimator_input, SyntheticControlInput):
            raise PermanentEstimationError("Synthetic-control input has an invalid shape.")
        matrix, units, periods, treated_unit, first_post = self._balanced_panel(
            estimator_input.observations
        )
        treated_index = units.index(treated_unit)
        donor_indices = [index for index in range(len(units)) if index != treated_index]
        treated = matrix[treated_index]
        donors = matrix[donor_indices].T
        fit = self._fit(treated=treated, donors=donors, first_post=first_post)
        effects = treated - fit.predicted
        average_effect = float(np.mean(effects[first_post:]))
        placebo_tests = self._placebos(
            matrix=matrix,
            units=units,
            first_post=first_post,
            treated_unit=treated_unit,
        )
        treated_ratio = self._safe_ratio(fit.post_rmspe, fit.pre_rmspe)
        placebo_ratios = [
            float(value)
            for item in placebo_tests
            if isinstance((value := item["rmspe_ratio"]), int | float)
        ]
        placebo_p_value = (1 + sum(ratio >= treated_ratio for ratio in placebo_ratios)) / (
            len(placebo_ratios) + 1
        )
        placebo_effects = [
            float(value)
            for item in placebo_tests
            if isinstance((value := item["average_effect"]), int | float)
        ]
        standard_error = max(float(np.std(placebo_effects, ddof=1)), 1e-9)
        normalized_pre_rmspe = fit.pre_rmspe / max(abs(float(np.mean(treated[:first_post]))), 1e-9)
        assessment, causal_allowed, warnings, conclusion = self._policy.assess(
            normalized_pre_rmspe=normalized_pre_rmspe,
            donor_count=len(donor_indices),
            placebo_p_value=placebo_p_value,
        )
        donor_weights = {
            units[index]: float(weight)
            for index, weight in zip(donor_indices, fit.weights, strict=True)
            if weight > 1e-8
        }
        counterfactual_post_mean = float(np.mean(fit.predicted[first_post:]))
        diagnostics: dict[str, object] = {
            "design_assessment": assessment,
            "causal_claim_allowed": causal_allowed,
            "donor_weights": donor_weights,
            "selected_donors": list(donor_weights),
            "pre_treatment_rmspe": fit.pre_rmspe,
            "normalized_pre_treatment_rmspe": normalized_pre_rmspe,
            "post_treatment_rmspe": fit.post_rmspe,
            "rmspe_ratio": treated_ratio,
            "placebo_p_value": placebo_p_value,
            "placebo_tests": placebo_tests,
            "observed_vs_counterfactual": [
                {
                    "period": period.isoformat(),
                    "observed": float(treated[index]),
                    "counterfactual": float(fit.predicted[index]),
                    "post_treatment": index >= first_post,
                }
                for index, period in enumerate(periods)
            ],
            "treatment_effects_over_time": [
                {
                    "period": periods[index].isoformat(),
                    "effect": float(effects[index]),
                }
                for index in range(first_post, len(periods))
            ],
            "confidence_evidence": {
                "method": "in-space placebo RMSPE ratios",
                "placebo_p_value": placebo_p_value,
                "placebo_count": len(placebo_tests),
            },
            "warnings": warnings,
            "plain_language_conclusion": conclusion,
            "model_specification": {
                "optimizer": "SLSQP",
                "constraints": "nonnegative donor weights summing to one",
            },
            "sample_counts": {
                "treated_units": 1,
                "control_units": len(donor_indices),
                "observations": len(estimator_input.observations),
            },
        }
        return AnalysisEstimationResult(
            effect=average_effect,
            standard_error=standard_error,
            p_value=placebo_p_value,
            confidence_interval_low=average_effect - 1.96 * standard_error,
            confidence_interval_high=average_effect + 1.96 * standard_error,
            observation_count=len(estimator_input.observations),
            library_name="scipy",
            library_version=scipy.__version__,
            diagnostics=diagnostics,
            incremental_outcome=float(np.sum(effects[first_post:])),
            relative_lift=(
                average_effect / counterfactual_post_mean
                if not math.isclose(counterfactual_post_mean, 0.0)
                else None
            ),
        )

    @staticmethod
    def _balanced_panel(
        observations: tuple[PanelObservation, ...],
    ) -> tuple[np.ndarray, list[str], list[datetime], str, int]:
        if not observations:
            raise PermanentEstimationError("Synthetic control requires panel observations.")
        units = sorted({item.unit for item in observations})
        periods = sorted({item.observed_at for item in observations})
        treated_units = {item.unit for item in observations if item.treated}
        if len(treated_units) != 1:
            raise PermanentEstimationError("Synthetic control requires exactly one treated unit.")
        if len(units) < 3:
            raise PermanentEstimationError("Synthetic control requires at least two donor units.")
        lookup = {(item.unit, item.observed_at): item for item in observations}
        if len(lookup) != len(units) * len(periods):
            raise PermanentEstimationError("Synthetic control requires a balanced panel.")
        matrix = np.asarray(
            [[lookup[(unit, period)].outcome for period in periods] for unit in units],
            dtype=float,
        )
        if not np.isfinite(matrix).all():
            raise PermanentEstimationError("Synthetic-control outcomes must be finite.")
        post_flags = [lookup[(units[0], period)].post_period for period in periods]
        if True not in post_flags or False not in post_flags:
            raise PermanentEstimationError("Synthetic control requires pre and post periods.")
        first_post = post_flags.index(True)
        if first_post < 3 or first_post == len(periods):
            raise PermanentEstimationError(
                "Synthetic control requires at least three pre-treatment periods."
            )
        return matrix, units, periods, next(iter(treated_units)), first_post

    @staticmethod
    def _fit(*, treated: np.ndarray, donors: np.ndarray, first_post: int) -> SyntheticControlFit:
        donor_count = donors.shape[1]
        solution = minimize(
            lambda weights: float(
                np.mean(np.square(treated[:first_post] - donors[:first_post] @ weights))
            ),
            np.full(donor_count, 1 / donor_count),
            method="SLSQP",
            bounds=[(0.0, 1.0)] * donor_count,
            constraints={"type": "eq", "fun": lambda weights: float(np.sum(weights) - 1)},
            options={"ftol": 1e-12, "maxiter": 1_000},
        )
        if not solution.success:
            raise PermanentEstimationError("Synthetic-control donor optimization failed.")
        predicted = donors @ solution.x
        return SyntheticControlFit(
            weights=np.asarray(solution.x, dtype=float),
            predicted=predicted,
            pre_rmspe=float(
                np.sqrt(np.mean(np.square(treated[:first_post] - predicted[:first_post])))
            ),
            post_rmspe=float(
                np.sqrt(np.mean(np.square(treated[first_post:] - predicted[first_post:])))
            ),
        )

    def _placebos(
        self,
        *,
        matrix: np.ndarray,
        units: list[str],
        first_post: int,
        treated_unit: str,
    ) -> list[dict[str, object]]:
        placebos: list[dict[str, object]] = []
        for target_index, unit in enumerate(units):
            donor_indices = [index for index in range(len(units)) if index != target_index]
            try:
                fit = self._fit(
                    treated=matrix[target_index],
                    donors=matrix[donor_indices].T,
                    first_post=first_post,
                )
            except PermanentEstimationError:
                continue
            effects = matrix[target_index] - fit.predicted
            placebos.append(
                {
                    "unit": unit,
                    "average_effect": float(np.mean(effects[first_post:])),
                    "pre_rmspe": fit.pre_rmspe,
                    "post_rmspe": fit.post_rmspe,
                    "rmspe_ratio": self._safe_ratio(fit.post_rmspe, fit.pre_rmspe),
                }
            )
        return [item for item in placebos if item["unit"] != treated_unit]

    @staticmethod
    def _safe_ratio(numerator: float, denominator: float) -> float:
        return numerator / max(denominator, 1e-9)
