from datetime import UTC, datetime, timedelta

from incrementality_api.application.analysis_execution.estimation import (
    MarketingMixInput,
    MarketingMixObservation,
)
from incrementality_api.infrastructure.estimation.marketing_mix_model import (
    BayesianMarketingMixEstimator,
    MarketingMixDesign,
    MarketingMixPosterior,
    MarketingMixTransformer,
)


class FakeModelRunner:
    def __init__(
        self,
        *,
        max_r_hat: float = 1.01,
        channel_coefficients: dict[str, tuple[float, float, float]] | None = None,
    ) -> None:
        self.design: MarketingMixDesign | None = None
        self.random_seeds: list[int] = []
        self.max_r_hat = max_r_hat
        self.channel_coefficients = channel_coefficients or {
            "search": (2.0, 1.5, 2.5),
            "social": (1.0, 0.5, 1.5),
        }

    def fit(
        self,
        design: MarketingMixDesign,
        *,
        random_seed: int,
    ) -> MarketingMixPosterior:
        self.design = design
        self.random_seeds.append(random_seed)
        return MarketingMixPosterior(
            channel_coefficients=self.channel_coefficients,
            intercept=50.0,
            noise_scale=2.0,
            max_r_hat=self.max_r_hat,
            min_effective_sample_size=800.0,
            divergences=0,
            library_name="pymc",
            library_version="6.1.0",
        )


def mmm_input(
    *,
    periods: int = 36,
    outcome_kind: str = "revenue",
) -> MarketingMixInput:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return MarketingMixInput(
        observations=tuple(
            MarketingMixObservation(
                observed_at=start + timedelta(days=7 * index),
                outcome=100 + index * 2,
                channel_spend={
                    "search": 20 + index,
                    "social": 10 + index * 0.5,
                },
            )
            for index in range(periods)
        ),
        adstock_decay={"search": 0.5, "social": 0.3},
        saturation_half_spend={"search": 30, "social": 20},
        seasonality_period=52,
        outcome_kind=outcome_kind,
    )


def test_fake_model_contract_produces_contributions_roas_and_scenarios() -> None:
    runner = FakeModelRunner()
    result = BayesianMarketingMixEstimator(
        model_runner=runner,
        transformer=MarketingMixTransformer(),
    ).estimate(
        mmm_input(),
        random_seed=1_729,
    )

    assert runner.design is not None
    assert runner.random_seeds == [1_729]
    assert result.library_name == "pymc"
    assert result.diagnostics["channel_contributions"]  # type: ignore[index]
    assert result.diagnostics["posterior_intervals"]  # type: ignore[index]
    assert result.diagnostics["channel_roas"]  # type: ignore[index]
    assert result.diagnostics["budget_response_curves"]  # type: ignore[index]
    assert result.diagnostics["scenario_plan"]  # type: ignore[index]
    assert result.diagnostics["design_assessment"] == "valid"


def test_mmm_persists_one_model_fit_record_per_observed_period() -> None:
    class FitSeriesRunner:
        def fit(
            self,
            design: MarketingMixDesign,
            *,
            random_seed: int,
        ):
            from types import SimpleNamespace

            fitted_outcome = tuple(
                (
                    float(observed) - 1.0,
                    float(observed) - 2.0,
                    float(observed),
                )
                for observed in design.outcomes
            )

            return SimpleNamespace(
                channel_coefficients={
                    "search": (2.0, 1.5, 2.5),
                    "social": (1.0, 0.5, 1.5),
                },
                intercept=50.0,
                noise_scale=2.0,
                fitted_outcome=fitted_outcome,
                max_r_hat=1.01,
                min_effective_sample_size=800.0,
                divergences=0,
                library_name="pymc",
                library_version="6.1.0",
            )

    result = BayesianMarketingMixEstimator(
        model_runner=FitSeriesRunner(),
        transformer=MarketingMixTransformer(),
    ).estimate(
        mmm_input(periods=36),
        random_seed=1_729,
    )

    series = result.diagnostics["model_fit_series"]

    assert len(series) == 36
    assert series[0] == {
        "period": "2024-01-01T00:00:00+00:00",
        "observed": 100.0,
        "fitted_mean": 99.0,
        "fitted_low": 98.0,
        "fitted_high": 100.0,
        "residual": 1.0,
    }
    assert series[-1]["period"] == "2024-09-02T00:00:00+00:00"


def test_channel_efficiency_semantics_follow_mmm_outcome_kind() -> None:
    revenue = BayesianMarketingMixEstimator(
        model_runner=FakeModelRunner(),
        transformer=MarketingMixTransformer(),
    ).estimate(
        mmm_input(outcome_kind="revenue"),
        random_seed=1_729,
    )

    conversions = BayesianMarketingMixEstimator(
        model_runner=FakeModelRunner(),
        transformer=MarketingMixTransformer(),
    ).estimate(
        mmm_input(outcome_kind="conversions"),
        random_seed=1_729,
    )

    generic = BayesianMarketingMixEstimator(
        model_runner=FakeModelRunner(),
        transformer=MarketingMixTransformer(),
    ).estimate(
        mmm_input(outcome_kind="outcome"),
        random_seed=1_729,
    )

    assert (
        revenue.diagnostics["channel_efficiency_metric"]
        == "incremental_revenue_per_dollar"
    )
    assert revenue.diagnostics["channel_efficiency"]
    assert revenue.diagnostics["channel_roas"] == revenue.diagnostics["channel_efficiency"]

    assert (
        conversions.diagnostics["channel_efficiency_metric"]
        == "incremental_conversions_per_dollar"
    )
    assert conversions.diagnostics["channel_efficiency"]
    assert "channel_roas" not in conversions.diagnostics

    assert (
        generic.diagnostics["channel_efficiency_metric"]
        == "incremental_outcome_units_per_dollar"
    )
    assert generic.diagnostics["channel_efficiency"]
    assert "channel_roas" not in generic.diagnostics


def test_convergence_failure_blocks_recommendations() -> None:
    result = BayesianMarketingMixEstimator(
        model_runner=FakeModelRunner(max_r_hat=1.2),
        transformer=MarketingMixTransformer(),
    ).estimate(mmm_input(), random_seed=1_729)

    assert result.diagnostics["design_assessment"] == "invalid"
    assert result.diagnostics["causal_claim_allowed"] is False
    assert result.diagnostics["scenario_plan"] == []


def test_very_wide_channel_posterior_blocks_budget_recommendations() -> None:
    runner = FakeModelRunner(
        channel_coefficients={
            "search": (2.0, 0.05, 6.0),
            "social": (1.0, 0.02, 4.0),
        }
    )

    result = BayesianMarketingMixEstimator(
        model_runner=runner,
        transformer=MarketingMixTransformer(),
    ).estimate(
        mmm_input(),
        random_seed=1_729,
    )

    assert result.diagnostics["design_assessment"] == "weak"
    assert result.diagnostics["recommendations_allowed"] is False
    assert result.diagnostics["scenario_plan"] == []

    warnings = result.diagnostics["warnings"]
    assert any(
        "posterior uncertainty" in str(warning).lower()
        for warning in warnings
    )

    conclusion = str(
        result.diagnostics["plain_language_conclusion"]
    )
    assert "posterior uncertainty" in conclusion.lower()
    assert "data history is limited" not in conclusion.lower()


def test_short_history_receives_weak_data_warning() -> None:
    result = BayesianMarketingMixEstimator(
        model_runner=FakeModelRunner(),
        transformer=MarketingMixTransformer(),
    ).estimate(mmm_input(periods=16), random_seed=1_729)

    assert result.diagnostics["design_assessment"] == "weak"
    assert result.diagnostics["warnings"]

def test_identical_seeded_mmm_contract_produces_identical_results() -> None:
    first_runner = FakeModelRunner()
    second_runner = FakeModelRunner()

    first = BayesianMarketingMixEstimator(
        model_runner=first_runner,
        transformer=MarketingMixTransformer(),
    ).estimate(
        mmm_input(),
        random_seed=1_729,
    )

    second = BayesianMarketingMixEstimator(
        model_runner=second_runner,
        transformer=MarketingMixTransformer(),
    ).estimate(
        mmm_input(),
        random_seed=1_729,
    )

    assert first_runner.random_seeds == [1_729]
    assert second_runner.random_seeds == [1_729]
    assert first == second
