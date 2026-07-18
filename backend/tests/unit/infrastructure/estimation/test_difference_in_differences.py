import pytest

from incrementality_api.application.analysis_execution.estimation import (
    DifferenceInDifferencesInput,
    DifferenceInDifferencesObservation,
    PermanentEstimationError,
)
from incrementality_api.infrastructure.estimation.difference_in_differences import (
    StatsmodelsDifferenceInDifferencesEstimator,
)


def build_panel() -> DifferenceInDifferencesInput:
    observations: list[DifferenceInDifferencesObservation] = []
    for unit_index in range(8):
        treated = unit_index >= 4
        for period in range(4):
            post_period = period >= 2
            outcome = 10.0 + unit_index + period
            if treated and post_period:
                outcome += 5.0
            observations.append(
                DifferenceInDifferencesObservation(
                    unit=f"unit-{unit_index}",
                    outcome=outcome,
                    treated=treated,
                    post_period=post_period,
                )
            )
    return DifferenceInDifferencesInput(observations=tuple(observations))


def test_estimates_difference_in_differences_effect_with_statsmodels() -> None:
    result = StatsmodelsDifferenceInDifferencesEstimator().estimate(
        build_panel(),
        random_seed=1_729,
    )

    assert result.effect == pytest.approx(5.0)
    assert result.observation_count == 32
    assert result.confidence_interval_low <= result.effect
    assert result.confidence_interval_high >= result.effect


def test_rejects_input_without_treated_and_control_groups() -> None:
    invalid = DifferenceInDifferencesInput(
        observations=(
            DifferenceInDifferencesObservation(
                unit="treated-only",
                outcome=1.0,
                treated=True,
                post_period=False,
            ),
            DifferenceInDifferencesObservation(
                unit="treated-only",
                outcome=2.0,
                treated=True,
                post_period=True,
            ),
        )
    )

    with pytest.raises(PermanentEstimationError, match="treated and control"):
        StatsmodelsDifferenceInDifferencesEstimator().estimate(
            invalid,
            random_seed=1_729,
        )


def test_identical_did_inputs_produce_identical_results() -> None:
    observations = tuple(
        DifferenceInDifferencesObservation(
            unit=f"unit-{unit_index}",
            outcome=(
                100
                + unit_index % 6
                + period
                + ((unit_index % 3) - 1) * period * 0.1
                + (
                    5
                    if unit_index >= 6 and period >= 4
                    else 0
                )
            ),
            treated=unit_index >= 6,
            post_period=period >= 4,
        )
        for unit_index in range(12)
        for period in range(6)
    )

    estimator_input = DifferenceInDifferencesInput(
        observations=observations,
    )

    estimator = StatsmodelsDifferenceInDifferencesEstimator()

    first = estimator.estimate(
        estimator_input,
        random_seed=1_729,
    )

    second = estimator.estimate(
        estimator_input,
        random_seed=1_729,
    )

    assert first == second
