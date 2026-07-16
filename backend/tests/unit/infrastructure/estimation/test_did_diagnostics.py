from datetime import UTC, datetime, timedelta

import pytest

from incrementality_api.application.analysis_execution.estimation import (
    DifferenceInDifferencesInput,
    DifferenceInDifferencesObservation,
)
from incrementality_api.infrastructure.estimation.difference_in_differences import (
    StatsmodelsDifferenceInDifferencesEstimator,
)


def panel(*, pretrend: float = 0.0, units: int = 12) -> DifferenceInDifferencesInput:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    observations: list[DifferenceInDifferencesObservation] = []
    for unit_index in range(units):
        treated = unit_index >= units // 2
        for period in range(6):
            post = period >= 4
            outcome = 100 + unit_index + period + ((unit_index % 3) - 1) * period * 0.15
            if treated:
                outcome += pretrend * period
            if treated and post:
                outcome += 8
            observations.append(
                DifferenceInDifferencesObservation(
                    unit=f"market-{unit_index}",
                    outcome=outcome,
                    treated=treated,
                    post_period=post,
                    observed_at=start + timedelta(days=period),
                )
            )
    return DifferenceInDifferencesInput(tuple(observations))


def test_valid_design_persists_structured_diagnostics_and_causal_conclusion() -> None:
    result = StatsmodelsDifferenceInDifferencesEstimator().estimate(panel(), random_seed=1_729)
    diagnostics = result.diagnostics

    assert diagnostics["design_assessment"] == "valid"
    assert diagnostics["causal_claim_allowed"] is True
    assert diagnostics["parallel_trends"]["passed"] is True  # type: ignore[index]
    assert len(diagnostics["event_study"]) == 6  # type: ignore[arg-type]
    assert diagnostics["sample_counts"]["treated_units"] == 6  # type: ignore[index]
    assert diagnostics["missing_data"]["total_missing"] == 0  # type: ignore[index]
    assert "causal" in str(diagnostics["plain_language_conclusion"]).lower()
    assert result.incremental_outcome == pytest.approx(result.effect * 12)


def test_invalid_parallel_trends_blocks_causal_language() -> None:
    result = StatsmodelsDifferenceInDifferencesEstimator().estimate(
        panel(pretrend=5.0), random_seed=1_729
    )
    diagnostics = result.diagnostics

    assert diagnostics["design_assessment"] == "invalid"
    assert diagnostics["causal_claim_allowed"] is False
    assert diagnostics["warnings"]
    assert "causal effect" not in str(diagnostics["plain_language_conclusion"]).lower()


def test_small_design_is_weak_and_does_not_allow_causal_claim() -> None:
    result = StatsmodelsDifferenceInDifferencesEstimator().estimate(
        panel(units=8), random_seed=1_729
    )

    assert result.diagnostics["design_assessment"] == "weak"
    assert result.diagnostics["causal_claim_allowed"] is False
