from datetime import UTC, datetime, timedelta

import pytest

from incrementality_api.application.analysis_execution.estimation import (
    PanelObservation,
    SyntheticControlInput,
)
from incrementality_api.infrastructure.estimation.synthetic_control import (
    ScipySyntheticControlEstimator,
)


def build_panel(*, poor_fit: bool = False) -> SyntheticControlInput:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    observations: list[PanelObservation] = []
    for period in range(10):
        post = period >= 7
        donor_a = 20 + period
        donor_b = 30 + period * 0.5
        donor_c = 25 + period * 0.8
        treated = 0.5 * donor_a + 0.3 * donor_b + 0.2 * donor_c
        if poor_fit and not post:
            treated += (-1) ** period * 20
        if post:
            treated += 8
        for unit, outcome, is_treated in (
            ("target", treated, True),
            ("donor-a", donor_a, False),
            ("donor-b", donor_b, False),
            ("donor-c", donor_c, False),
        ):
            observations.append(
                PanelObservation(
                    unit=unit,
                    observed_at=start + timedelta(days=period),
                    outcome=outcome,
                    treated=is_treated,
                    post_period=post,
                )
            )
    return SyntheticControlInput(tuple(observations))


def test_selects_constrained_donors_and_estimates_effect_over_time() -> None:
    result = ScipySyntheticControlEstimator().estimate(build_panel())
    diagnostics = result.diagnostics

    weights = diagnostics["donor_weights"]
    assert sum(weights.values()) == pytest.approx(1.0)  # type: ignore[union-attr]
    assert all(value >= 0 for value in weights.values())  # type: ignore[union-attr]
    assert result.effect == pytest.approx(8.0, abs=0.25)
    assert diagnostics["pre_treatment_rmspe"] < 0.1  # type: ignore[operator]
    assert len(diagnostics["treatment_effects_over_time"]) == 3  # type: ignore[arg-type]
    assert diagnostics["placebo_tests"]  # type: ignore[index]
    assert diagnostics["causal_claim_allowed"] is True


def test_poor_pre_period_fit_is_invalid_and_blocks_causal_claim() -> None:
    result = ScipySyntheticControlEstimator().estimate(build_panel(poor_fit=True))

    assert result.diagnostics["design_assessment"] == "invalid"
    assert result.diagnostics["causal_claim_allowed"] is False
    assert result.diagnostics["warnings"]
