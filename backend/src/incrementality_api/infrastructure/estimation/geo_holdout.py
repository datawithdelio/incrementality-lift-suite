import math
from collections import defaultdict

import numpy as np

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
    DifferenceInDifferencesInput,
    DifferenceInDifferencesObservation,
    GeoHoldoutInput,
    PermanentEstimationError,
)
from incrementality_api.infrastructure.estimation.difference_in_differences import (
    StatsmodelsDifferenceInDifferencesEstimator,
)


class GeoHoldoutDiagnosticPolicy:
    """Apply product-specific geo balance and sample-size rules."""

    def assess(
        self,
        *,
        parallel_trends_passed: bool,
        standardized_mean_difference: float,
        treated_units: int,
        control_units: int,
    ) -> tuple[str, bool, list[str], str]:
        warnings: list[str] = []
        if not parallel_trends_passed:
            warnings.append("Treated and holdout geographies have different pre-period trends.")
        if abs(standardized_mean_difference) > 0.25:
            warnings.append("Pre-period outcome levels are not well balanced across geo groups.")
        if treated_units < 5 or control_units < 5:
            warnings.append("The experiment has fewer than five geographies in one group.")
        if not parallel_trends_passed or abs(standardized_mean_difference) > 1:
            return (
                "invalid",
                False,
                warnings,
                "The geographic design is not comparable enough for a causal conclusion.",
            )
        if warnings:
            return (
                "weak",
                False,
                warnings,
                "The geographic estimate is directional but needs a stronger comparison group.",
            )
        return (
            "valid",
            True,
            warnings,
            "The balanced geo holdout supports a credible incremental campaign effect.",
        )


class StatsmodelsGeoHoldoutEstimator:
    """Estimate geo lift with clustered DiD while keeping geo policy custom."""

    def __init__(self, policy: GeoHoldoutDiagnosticPolicy | None = None) -> None:
        self._policy = policy or GeoHoldoutDiagnosticPolicy()
        self._estimator = StatsmodelsDifferenceInDifferencesEstimator()

    def estimate(
        self,
        estimator_input: object,
        *,
        random_seed: int,
    ) -> AnalysisEstimationResult:
        if not isinstance(estimator_input, GeoHoldoutInput):
            raise PermanentEstimationError("Geo-holdout input has an invalid shape.")
        observations = estimator_input.observations
        if not observations:
            raise PermanentEstimationError("Geo holdout requires observations.")
        units = {item.unit for item in observations}
        missing_coordinates = units.difference(estimator_input.coordinates)
        if missing_coordinates:
            raise PermanentEstimationError("Every geography requires map coordinates.")
        did_input = DifferenceInDifferencesInput(
            tuple(
                DifferenceInDifferencesObservation(
                    unit=item.unit,
                    outcome=item.outcome,
                    treated=item.treated,
                    post_period=item.post_period,
                    observed_at=item.observed_at,
                )
                for item in observations
            )
        )
        base = self._estimator.estimate(
            did_input,
            random_seed=random_seed,
        )
        base_diagnostics = dict(base.diagnostics)
        parallel = base_diagnostics.get("parallel_trends")
        parallel_mapping = parallel if isinstance(parallel, dict) else {}
        pre_unit_means: defaultdict[tuple[bool, str], list[float]] = defaultdict(list)
        for item in observations:
            if not item.post_period:
                pre_unit_means[(item.treated, item.unit)].append(item.outcome)
        treated_pre = np.asarray(
            [np.mean(values) for (treated, _), values in pre_unit_means.items() if treated]
        )
        control_pre = np.asarray(
            [np.mean(values) for (treated, _), values in pre_unit_means.items() if not treated]
        )
        pooled_standard_deviation = math.sqrt(
            (float(np.var(treated_pre)) + float(np.var(control_pre))) / 2
        )
        standardized_difference = float(np.mean(treated_pre) - np.mean(control_pre)) / max(
            pooled_standard_deviation, 1e-9
        )
        treated_units = len({item.unit for item in observations if item.treated})
        control_units = len({item.unit for item in observations if not item.treated})
        assessment, causal_allowed, warnings, conclusion = self._policy.assess(
            parallel_trends_passed=parallel_mapping.get("passed") is True,
            standardized_mean_difference=standardized_difference,
            treated_units=treated_units,
            control_units=control_units,
        )
        spillover_warnings = [
            {
                "treated_geo": treated_geo,
                "control_geo": control_geo,
                "message": (
                    "Adjacent treated and holdout geographies may exchange campaign exposure."
                ),
            }
            for treated_geo, control_geo in estimator_input.spillover_pairs
        ]
        grouped: defaultdict[str, list[float]] = defaultdict(list)
        for item in observations:
            grouped[item.unit].append(item.outcome)
        assignments = [
            {
                "geo": unit,
                "latitude": estimator_input.coordinates[unit].latitude,
                "longitude": estimator_input.coordinates[unit].longitude,
                "assignment": (
                    "treatment"
                    if next(item for item in observations if item.unit == unit).treated
                    else "holdout"
                ),
                "average_outcome": float(np.mean(grouped[unit])),
            }
            for unit in sorted(units)
        ]
        diagnostics: dict[str, object] = {
            **base_diagnostics,
            "design_assessment": assessment,
            "causal_claim_allowed": causal_allowed,
            "balance_diagnostics": {
                "standardized_mean_difference": standardized_difference,
                "parallel_trends_passed": parallel_mapping.get("passed") is True,
                "treated_pre_mean": float(np.mean(treated_pre)),
                "control_pre_mean": float(np.mean(control_pre)),
            },
            "geographic_assignments": assignments,
            "spillover_warnings": spillover_warnings,
            "warnings": warnings + [item["message"] for item in spillover_warnings],
            "plain_language_conclusion": conclusion,
            "outcome_kind": estimator_input.outcome_kind,
        }
        treated_post_count = sum(item.treated and item.post_period for item in observations)
        impact = base.effect * treated_post_count
        return AnalysisEstimationResult(
            effect=base.effect,
            standard_error=base.standard_error,
            p_value=base.p_value,
            confidence_interval_low=base.confidence_interval_low,
            confidence_interval_high=base.confidence_interval_high,
            observation_count=base.observation_count,
            library_name=base.library_name,
            library_version=base.library_version,
            diagnostics=diagnostics,
            incremental_outcome=impact,
            relative_lift=base.relative_lift,
            incremental_revenue=(impact if estimator_input.outcome_kind == "revenue" else None),
            incremental_conversions=(
                impact if estimator_input.outcome_kind == "conversions" else None
            ),
        )
