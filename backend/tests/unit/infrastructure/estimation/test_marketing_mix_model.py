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
    def __init__(self, *, max_r_hat: float = 1.01) -> None:
        self.design: MarketingMixDesign | None = None
        self.random_seeds: list[int] = []
        self.max_r_hat = max_r_hat

    def fit(
        self,
        design: MarketingMixDesign,
        *,
        random_seed: int,
    ) -> MarketingMixPosterior:
        self.design = design
        self.random_seeds.append(random_seed)
        return MarketingMixPosterior(
            channel_coefficients={
                "search": (2.0, 1.5, 2.5),
                "social": (1.0, 0.5, 1.5),
            },
            intercept=50.0,
            noise_scale=2.0,
            max_r_hat=self.max_r_hat,
            min_effective_sample_size=800.0,
            divergences=0,
            library_name="pymc",
            library_version="6.1.0",
        )


def mmm_input(*, periods: int = 36) -> MarketingMixInput:
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
        outcome_kind="revenue",
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


def test_convergence_failure_blocks_recommendations() -> None:
    result = BayesianMarketingMixEstimator(
        model_runner=FakeModelRunner(max_r_hat=1.2),
        transformer=MarketingMixTransformer(),
    ).estimate(mmm_input(), random_seed=1_729)

    assert result.diagnostics["design_assessment"] == "invalid"
    assert result.diagnostics["causal_claim_allowed"] is False
    assert result.diagnostics["scenario_plan"] == []


def test_short_history_receives_weak_data_warning() -> None:
    result = BayesianMarketingMixEstimator(
        model_runner=FakeModelRunner(),
        transformer=MarketingMixTransformer(),
    ).estimate(mmm_input(periods=16), random_seed=1_729)

    assert result.diagnostics["design_assessment"] == "weak"
    assert result.diagnostics["warnings"]
