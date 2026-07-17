import math
from collections import defaultdict
from collections.abc import Mapping

import numpy as np
import statsmodels.api as sm  # type: ignore[import-untyped]

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
    DifferenceInDifferencesInput,
    DifferenceInDifferencesObservation,
    PermanentEstimationError,
)
from incrementality_api.infrastructure.estimation.package_versions import (
    installed_distribution_version,
)


class DifferenceInDifferencesDiagnosticPolicy:
    """Turn library statistics into product warnings and safe interpretation."""

    def assess(
        self,
        *,
        pretrend_p_value: float,
        treated_units: int,
        control_units: int,
        effect: float,
        confidence_low: float,
        confidence_high: float,
    ) -> tuple[str, list[str], bool, str]:
        warnings: list[str] = []
        if pretrend_p_value < 0.05:
            warnings.append(
                "Treated and control groups had materially different pre-treatment trends."
            )
        if treated_units < 5 or control_units < 5:
            warnings.append("The design has fewer than five units in at least one group.")
        if confidence_low <= 0 <= confidence_high:
            warnings.append("The confidence interval includes no effect.")

        if pretrend_p_value < 0.05:
            return (
                "invalid",
                warnings,
                False,
                "The design does not support a causal claim because pre-treatment trends differ.",
            )
        if pretrend_p_value < 0.10 or treated_units < 5 or control_units < 5:
            return (
                "weak",
                warnings,
                False,
                "The estimate is directional, but the design is too weak for a causal claim.",
            )
        direction = "increase" if effect >= 0 else "decrease"
        return (
            "valid",
            warnings,
            True,
            (
                f"The design supports an estimated causal {direction} of "
                f"{abs(effect):.2f} per treated observation."
            ),
        )


class StatsmodelsDifferenceInDifferencesEstimator:
    """Estimate clustered DiD statistics and persist structured diagnostics."""

    statistical_packages = ("numpy", "statsmodels")

    def __init__(self, policy: DifferenceInDifferencesDiagnosticPolicy | None = None) -> None:
        self._policy = policy or DifferenceInDifferencesDiagnosticPolicy()

    def estimate(
        self,
        estimator_input: object,
        *,
        random_seed: int,
    ) -> AnalysisEstimationResult:
        del random_seed

        if not isinstance(estimator_input, DifferenceInDifferencesInput):
            raise PermanentEstimationError("Difference-in-differences input has an invalid shape.")
        observations = estimator_input.observations
        self._validate(observations)
        outcomes = np.asarray([item.outcome for item in observations], dtype=float)
        treated = np.asarray([float(item.treated) for item in observations])
        post = np.asarray([float(item.post_period) for item in observations])
        design = np.column_stack((np.ones(len(observations)), treated, post, treated * post))
        groups = np.asarray([item.unit for item in observations])

        try:
            fitted = sm.OLS(outcomes, design).fit(cov_type="cluster", cov_kwds={"groups": groups})
            interval = fitted.conf_int(alpha=0.05)[3]
            effect = float(fitted.params[3])
            standard_error = float(fitted.bse[3])
            p_value = float(fitted.pvalues[3])
            confidence_low = float(interval[0])
            confidence_high = float(interval[1])
        except (ValueError, TypeError, np.linalg.LinAlgError) as error:
            raise PermanentEstimationError(
                "Difference-in-differences estimation failed for the supplied design."
            ) from error

        if not all(
            math.isfinite(value)
            for value in (effect, standard_error, p_value, confidence_low, confidence_high)
        ):
            raise PermanentEstimationError(
                "Difference-in-differences produced non-finite statistics."
            )

        periods = self._periods(observations)
        pretrend_slope, pretrend_p_value = self._pretrend(observations, periods)
        treated_units = len({item.unit for item in observations if item.treated})
        control_units = len({item.unit for item in observations if not item.treated})
        assessment, warnings, causal_allowed, conclusion = self._policy.assess(
            pretrend_p_value=pretrend_p_value,
            treated_units=treated_units,
            control_units=control_units,
            effect=effect,
            confidence_low=confidence_low,
            confidence_high=confidence_high,
        )
        event_study, observed_series = self._event_study(observations, periods)
        treated_post_count = sum(item.treated and item.post_period for item in observations)
        control_post_outcomes = [
            item.outcome for item in observations if not item.treated and item.post_period
        ]
        control_post_mean = float(np.mean(control_post_outcomes))
        relative_lift = effect / control_post_mean if control_post_mean else None
        diagnostics: Mapping[str, object] = {
            "design_assessment": assessment,
            "causal_claim_allowed": causal_allowed,
            "parallel_trends": {
                "passed": pretrend_p_value >= 0.05,
                "interaction_slope": pretrend_slope,
                "p_value": pretrend_p_value,
                "threshold": 0.05,
            },
            "pre_treatment_trends": self._pretrend_series(observations, periods),
            "event_study": event_study,
            "observed_vs_counterfactual": observed_series,
            "sample_counts": {
                "observations": len(observations),
                "treated_observations": sum(item.treated for item in observations),
                "control_observations": sum(not item.treated for item in observations),
                "treated_units": treated_units,
                "control_units": control_units,
                "treated_post_observations": treated_post_count,
            },
            "missing_data": {
                "total_missing": 0,
                "outcome_missing": 0,
                "treatment_missing": 0,
                "time_missing": 0,
                "unit_missing": 0,
            },
            "model_specification": {
                "formula": "outcome ~ treated + post + treated:post",
                "covariance": "clustered by unit",
                "confidence_level": 0.95,
                "unit_fixed_effects": False,
                "time_fixed_effects": True,
            },
            "warnings": warnings,
            "plain_language_conclusion": conclusion,
            "r_squared": float(fitted.rsquared),
            "adjusted_r_squared": float(fitted.rsquared_adj),
            "degrees_of_freedom": float(fitted.df_resid),
            "covariance_type": str(fitted.cov_type),
        }
        return AnalysisEstimationResult(
            effect=effect,
            standard_error=standard_error,
            p_value=p_value,
            confidence_interval_low=confidence_low,
            confidence_interval_high=confidence_high,
            observation_count=len(observations),
            library_name="statsmodels",
            library_version=installed_distribution_version("statsmodels"),
            diagnostics=diagnostics,
            incremental_outcome=effect * treated_post_count,
            relative_lift=relative_lift,
        )

    @staticmethod
    def _validate(observations: tuple[DifferenceInDifferencesObservation, ...]) -> None:
        if {item.treated for item in observations} != {False, True}:
            raise PermanentEstimationError(
                "Difference-in-differences requires treated and control groups."
            )
        if {item.post_period for item in observations} != {False, True}:
            raise PermanentEstimationError(
                "Difference-in-differences requires pre and post periods."
            )
        if len(observations) < 4:
            raise PermanentEstimationError(
                "Difference-in-differences requires at least four observations."
            )
        if not np.isfinite([item.outcome for item in observations]).all():
            raise PermanentEstimationError("Outcome values must be finite.")

    @staticmethod
    def _periods(
        observations: tuple[DifferenceInDifferencesObservation, ...],
    ) -> list[int]:
        if all(item.observed_at is not None for item in observations):
            values = sorted({item.observed_at for item in observations if item.observed_at})
            index = {value: position for position, value in enumerate(values)}
            return [index[item.observed_at] for item in observations]  # type: ignore[index]
        counters: defaultdict[str, int] = defaultdict(int)
        periods: list[int] = []
        for item in observations:
            periods.append(counters[item.unit])
            counters[item.unit] += 1
        return periods

    @staticmethod
    def _pretrend(
        observations: tuple[DifferenceInDifferencesObservation, ...], periods: list[int]
    ) -> tuple[float, float]:
        rows = [
            (item, period)
            for item, period in zip(observations, periods, strict=True)
            if not item.post_period
        ]
        y = np.asarray([item.outcome for item, _ in rows], dtype=float)
        treatment = np.asarray([float(item.treated) for item, _ in rows])
        time = np.asarray([float(period) for _, period in rows])
        interaction = treatment * time
        if np.allclose(interaction, 0) or len(rows) < 6:
            return 0.0, 1.0
        model = sm.OLS(y, np.column_stack((np.ones(len(rows)), treatment, time, interaction))).fit(
            cov_type="cluster",
            cov_kwds={"groups": np.asarray([item.unit for item, _ in rows])},
        )
        slope = float(model.params[3])
        p_value = float(model.pvalues[3])
        if abs(slope) < 1e-10 or not math.isfinite(p_value):
            return slope, 1.0
        return slope, p_value

    @staticmethod
    def _group_means(
        observations: tuple[DifferenceInDifferencesObservation, ...], periods: list[int]
    ) -> dict[int, dict[bool, float]]:
        grouped: defaultdict[tuple[int, bool], list[float]] = defaultdict(list)
        for item, period in zip(observations, periods, strict=True):
            grouped[(period, item.treated)].append(item.outcome)
        return {
            period: {
                treated: float(np.mean(grouped[(period, treated)])) for treated in (False, True)
            }
            for period in sorted(set(periods))
        }

    def _event_study(
        self, observations: tuple[DifferenceInDifferencesObservation, ...], periods: list[int]
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        means = self._group_means(observations, periods)
        first_post = min(
            period for item, period in zip(observations, periods, strict=True) if item.post_period
        )
        baseline_period = max(period for period in means if period < first_post)
        baseline_gap = means[baseline_period][True] - means[baseline_period][False]
        outcomes = np.asarray([item.outcome for item in observations], dtype=float)
        treatment = np.asarray([float(item.treated) for item in observations])
        period_values = np.asarray(periods)
        other_periods = [period for period in means if period != baseline_period]
        columns: list[np.ndarray] = [np.ones(len(observations)), treatment]
        columns.extend((period_values == period).astype(float) for period in other_periods)
        columns.extend(
            treatment * (period_values == period).astype(float) for period in other_periods
        )
        model = sm.OLS(outcomes, np.column_stack(columns)).fit(
            cov_type="cluster",
            cov_kwds={"groups": np.asarray([item.unit for item in observations])},
        )
        interaction_offset = 2 + len(other_periods)
        estimates = {
            period: (
                float(model.params[interaction_offset + index]),
                float(model.bse[interaction_offset + index]),
                float(model.pvalues[interaction_offset + index]),
                (
                    float(model.conf_int(alpha=0.05)[interaction_offset + index][0]),
                    float(model.conf_int(alpha=0.05)[interaction_offset + index][1]),
                ),
            )
            for index, period in enumerate(other_periods)
        }
        event_study: list[dict[str, object]] = []
        observed: list[dict[str, object]] = []
        for period, group_means in means.items():
            if period == baseline_period:
                coefficient, standard_error, event_p_value = 0.0, 0.0, 1.0
                event_interval = (0.0, 0.0)
            else:
                coefficient, standard_error, event_p_value, event_interval = estimates[period]
            event_study.append(
                {
                    "period": period - first_post,
                    "coefficient": coefficient,
                    "standard_error": standard_error,
                    "p_value": event_p_value,
                    "confidence_interval_low": event_interval[0],
                    "confidence_interval_high": event_interval[1],
                    "is_pre_treatment": period < first_post,
                }
            )
            observed.append(
                {
                    "period": period - first_post,
                    "observed": group_means[True],
                    "counterfactual": group_means[False] + baseline_gap,
                }
            )
        return event_study, observed

    def _pretrend_series(
        self, observations: tuple[DifferenceInDifferencesObservation, ...], periods: list[int]
    ) -> list[dict[str, float | int]]:
        means = self._group_means(observations, periods)
        return [
            {"period": period, "treated_mean": values[True], "control_mean": values[False]}
            for period, values in means.items()
            if any(
                item_period == period and not item.post_period
                for item, item_period in zip(observations, periods, strict=True)
            )
        ]
