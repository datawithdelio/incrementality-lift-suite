import math
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import numpy as np

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
    MarketingMixInput,
    PermanentEstimationError,
)
from incrementality_api.infrastructure.estimation.package_versions import (
    installed_distribution_version,
)


@dataclass(frozen=True, slots=True)
class MarketingMixDesign:
    channel_names: tuple[str, ...]
    control_names: tuple[str, ...]
    observed_at: tuple[datetime, ...]
    outcomes: np.ndarray
    raw_spend: np.ndarray
    controls: np.ndarray
    transformed_channels: np.ndarray
    seasonality: np.ndarray


@dataclass(frozen=True, slots=True)
class MarketingMixPosterior:
    channel_coefficients: dict[str, tuple[float, float, float]]
    intercept: float
    noise_scale: float
    max_r_hat: float
    min_effective_sample_size: float
    divergences: int
    library_name: str
    library_version: str
    fitted_outcome: tuple[tuple[float, float, float], ...] = ()


class MarketingMixModelRunner(Protocol):
    def fit(
        self,
        design: MarketingMixDesign,
        *,
        random_seed: int,
    ) -> MarketingMixPosterior:
        """Fit one Bayesian model using the supplied execution seed."""


class MarketingMixTransformer:
    """Build adstock, saturation, and seasonality outside PyMC."""

    def transform(self, model_input: MarketingMixInput) -> MarketingMixDesign:
        observations = sorted(model_input.observations, key=lambda item: item.observed_at)
        if len(observations) < 12:
            raise PermanentEstimationError("Marketing mix modeling requires at least 12 periods.")
        channel_names = tuple(sorted(observations[0].channel_spend))
        if not channel_names:
            raise PermanentEstimationError("Marketing mix modeling requires channel spend.")
        if any(tuple(sorted(item.channel_spend)) != channel_names for item in observations):
            raise PermanentEstimationError("Channel spend columns must be consistent by period.")
        control_names = tuple(sorted(observations[0].controls))
        if any(tuple(sorted(item.controls)) != control_names for item in observations):
            raise PermanentEstimationError("MMM control columns must be consistent by period.")
        raw_spend = np.asarray(
            [[item.channel_spend[name] for name in channel_names] for item in observations],
            dtype=float,
        )
        outcomes = np.asarray([item.outcome for item in observations], dtype=float)
        controls = np.asarray(
            [[item.controls[name] for name in control_names] for item in observations],
            dtype=float,
        ).reshape(len(observations), len(control_names))
        if (
            not np.isfinite(raw_spend).all()
            or not np.isfinite(controls).all()
            or not np.isfinite(outcomes).all()
        ):
            raise PermanentEstimationError(
                "MMM outcomes, channel spend, and controls must be finite."
            )
        if (raw_spend < 0).any():
            raise PermanentEstimationError("MMM channel spend must be nonnegative.")
        transformed = np.zeros_like(raw_spend)
        for channel_index, channel in enumerate(channel_names):
            decay = float(model_input.adstock_decay.get(channel, 0.5))
            half_spend = float(
                model_input.saturation_half_spend.get(
                    channel, max(float(np.median(raw_spend[:, channel_index])), 1.0)
                )
            )
            if not 0 <= decay < 1 or half_spend <= 0:
                raise PermanentEstimationError("MMM adstock and saturation settings are invalid.")
            adstocked = np.zeros(len(observations))
            for period_index, spend in enumerate(raw_spend[:, channel_index]):
                carryover = adstocked[period_index - 1] * decay if period_index else 0.0
                adstocked[period_index] = spend + carryover
            transformed[:, channel_index] = adstocked / (adstocked + half_spend)
        seasonality_period = model_input.seasonality_period
        if seasonality_period <= 1:
            raise PermanentEstimationError("MMM seasonality period must be greater than one.")
        time = np.arange(len(observations), dtype=float)
        seasonality = np.column_stack(
            (
                np.sin(2 * np.pi * time / seasonality_period),
                np.cos(2 * np.pi * time / seasonality_period),
            )
        )
        return MarketingMixDesign(
            channel_names=channel_names,
            control_names=control_names,
            observed_at=tuple(item.observed_at for item in observations),
            outcomes=outcomes,
            raw_spend=raw_spend,
            controls=controls,
            transformed_channels=transformed,
            seasonality=seasonality,
        )


class PyMCMarketingMixModelRunner:
    """Thin PyMC infrastructure adapter; all feature policy stays outside."""

    def __init__(
        self,
        *,
        draws: int = 500,
        tune: int = 500,
        chains: int = 2,
    ) -> None:
        self._draws = draws
        self._tune = tune
        self._chains = chains

    def fit(
        self,
        design: MarketingMixDesign,
        *,
        random_seed: int,
    ) -> MarketingMixPosterior:
        try:
            import pymc as pm  # type: ignore[import-untyped]
        except ImportError as error:
            raise PermanentEstimationError(
                "PyMC is unavailable for marketing mix modeling."
            ) from error

        outcome_scale = max(float(np.std(design.outcomes)), 1.0)
        with pm.Model(
            coords={
                "channel": design.channel_names,
                "period": tuple(range(len(design.outcomes))),
            }
        ):
            intercept = pm.Normal(
                "intercept",
                mu=float(np.mean(design.outcomes)),
                sigma=outcome_scale * 2,
            )
            beta = pm.HalfNormal("beta", sigma=outcome_scale, dims="channel")
            season_beta = pm.Normal("season_beta", mu=0, sigma=outcome_scale, shape=2)
            sigma = pm.HalfNormal("sigma", sigma=outcome_scale)
            mu = (
                intercept
                + pm.math.dot(design.transformed_channels, beta)
                + pm.math.dot(design.seasonality, season_beta)
            )
            if design.control_names:
                control_beta = pm.Normal(
                    "control_beta",
                    mu=0,
                    sigma=outcome_scale,
                    shape=len(design.control_names),
                )
                mu = mu + pm.math.dot(design.controls, control_beta)
            fitted_mean = pm.Deterministic(
                "fitted_mean",
                mu,
                dims="period",
            )
            pm.Normal(
                "outcome",
                mu=fitted_mean,
                sigma=sigma,
                observed=design.outcomes,
                dims="period",
            )
            inference = pm.sample(
                draws=self._draws,
                tune=self._tune,
                chains=self._chains,
                cores=1,
                target_accept=0.9,
                random_seed=random_seed,
                progressbar=False,
                return_inferencedata=True,
            )
        beta_samples = np.asarray(inference.posterior["beta"]).reshape(
            -1, len(design.channel_names)
        )
        coefficients = {
            channel: (
                float(np.mean(beta_samples[:, index])),
                float(np.quantile(beta_samples[:, index], 0.025)),
                float(np.quantile(beta_samples[:, index], 0.975)),
            )
            for index, channel in enumerate(design.channel_names)
        }
        fitted_samples = np.asarray(
            inference.posterior["fitted_mean"]
        ).reshape(-1, len(design.outcomes))
        fitted_outcome = tuple(
            (
                float(np.mean(fitted_samples[:, index])),
                float(np.quantile(fitted_samples[:, index], 0.025)),
                float(np.quantile(fitted_samples[:, index], 0.975)),
            )
            for index in range(len(design.outcomes))
        )

        r_hat = np.asarray(pm.rhat(inference, var_names=["beta"])["beta"])
        ess = np.asarray(pm.ess(inference, var_names=["beta"])["beta"])
        divergences = int(np.asarray(inference.sample_stats["diverging"]).sum())
        return MarketingMixPosterior(
            channel_coefficients=coefficients,
            intercept=float(np.asarray(inference.posterior["intercept"]).mean()),
            noise_scale=float(np.asarray(inference.posterior["sigma"]).mean()),
            max_r_hat=float(np.max(r_hat)),
            min_effective_sample_size=float(np.min(ess)),
            divergences=divergences,
            library_name="pymc",
            library_version=installed_distribution_version("pymc"),
            fitted_outcome=fitted_outcome,
        )


class MarketingMixDiagnosticPolicy:
    def assess(
        self, *, periods: int, channels: int, posterior: MarketingMixPosterior
    ) -> tuple[str, bool, list[str], str]:
        warnings: list[str] = []
        if posterior.max_r_hat > 1.05:
            warnings.append("Posterior chains did not converge reliably.")
        if posterior.min_effective_sample_size < 400:
            warnings.append("Posterior effective sample size is too small.")
        if posterior.divergences:
            warnings.append("The Bayesian sampler reported divergent transitions.")
        if periods < 24:
            warnings.append("Fewer than 24 periods limits separation of media and seasonality.")
        if periods < channels * 8:
            warnings.append("The history is short relative to the number of channels.")

        wide_channel_posteriors = [
            channel
            for channel, (mean, low, high) in posterior.channel_coefficients.items()
            if (high - low) / max(abs(mean), 1e-9) > 2.0
        ]
        if wide_channel_posteriors:
            warnings.append(
                "Posterior uncertainty is too wide for stable channel-level "
                "budget recommendations."
            )

        convergence_failed = (
            posterior.max_r_hat > 1.05
            or posterior.min_effective_sample_size < 400
            or posterior.divergences > 0
        )
        if convergence_failed:
            return (
                "invalid",
                False,
                warnings,
                "The model did not converge, so budget recommendations are withheld.",
            )
        if wide_channel_posteriors:
            return (
                "weak",
                False,
                warnings,
                "Posterior uncertainty is too wide for stable channel-level "
                "interpretation, so budget recommendations are withheld.",
            )

        if warnings:
            return (
                "weak",
                False,
                warnings,
                "The model is usable for exploration, but the data history is limited.",
            )
        return (
            "valid",
            True,
            warnings,
            "The posterior is stable enough for channel planning and scenario comparison.",
        )


class BayesianMarketingMixEstimator:
    statistical_packages = ("arviz", "numpy", "pymc", "pytensor")

    """Orchestrate custom MMM transformation and interpretation around PyMC."""

    def __init__(
        self,
        *,
        model_runner: MarketingMixModelRunner,
        transformer: MarketingMixTransformer,
        policy: MarketingMixDiagnosticPolicy | None = None,
    ) -> None:
        self._model_runner = model_runner
        self._transformer = transformer
        self._policy = policy or MarketingMixDiagnosticPolicy()

    def estimate(
        self,
        estimator_input: object,
        *,
        random_seed: int,
    ) -> AnalysisEstimationResult:
        if not isinstance(estimator_input, MarketingMixInput):
            raise PermanentEstimationError("Marketing-mix input has an invalid shape.")
        design = self._transformer.transform(estimator_input)
        posterior = self._model_runner.fit(
            design,
            random_seed=random_seed,
        )
        assessment, recommendations_allowed, warnings, conclusion = self._policy.assess(
            periods=len(design.outcomes),
            channels=len(design.channel_names),
            posterior=posterior,
        )
        contribution: dict[str, float] = {}
        intervals: dict[str, dict[str, float]] = {}
        efficiency: dict[str, float | None] = {}
        curves: dict[str, list[dict[str, float]]] = {}
        for channel_index, channel in enumerate(design.channel_names):
            mean, low, high = posterior.channel_coefficients[channel]
            exposure = float(np.sum(design.transformed_channels[:, channel_index]))
            channel_contribution = mean * exposure
            contribution[channel] = channel_contribution
            intervals[channel] = {"low": low * exposure, "high": high * exposure}
            spend = float(np.sum(design.raw_spend[:, channel_index]))
            efficiency[channel] = (
                channel_contribution / spend if spend > 0 else None
            )
            curves[channel] = self._response_curve(
                coefficient=mean,
                average_spend=float(np.mean(design.raw_spend[:, channel_index])),
                half_spend=float(estimator_input.saturation_half_spend.get(channel, 1.0)),
            )
        efficiency_metric = {
            "revenue": "incremental_revenue_per_dollar",
            "conversions": "incremental_conversions_per_dollar",
            "outcome": "incremental_outcome_units_per_dollar",
        }[estimator_input.outcome_kind]

        fitted_outcome = tuple(getattr(posterior, "fitted_outcome", ()))
        model_fit_series: list[dict[str, object]] = []

        if len(fitted_outcome) == len(design.outcomes):
            for period, observed, fitted in zip(
                design.observed_at,
                design.outcomes,
                fitted_outcome,
                strict=True,
            ):
                fitted_mean, fitted_low, fitted_high = fitted
                model_fit_series.append(
                    {
                        "period": period.isoformat(),
                        "observed": float(observed),
                        "fitted_mean": float(fitted_mean),
                        "fitted_low": float(fitted_low),
                        "fitted_high": float(fitted_high),
                        "residual": float(observed) - float(fitted_mean),
                    }
                )

        total = float(sum(contribution.values()))
        total_low = float(sum(item["low"] for item in intervals.values()))
        total_high = float(sum(item["high"] for item in intervals.values()))
        effect = total / len(design.outcomes)
        effect_low = total_low / len(design.outcomes)
        effect_high = total_high / len(design.outcomes)
        standard_error = max((effect_high - effect_low) / 3.92, 1e-9)
        diagnostics: dict[str, object] = {
            "design_assessment": assessment,
            "causal_claim_allowed": False,
            "recommendations_allowed": recommendations_allowed,
            "channel_contributions": contribution,
            "channel_spend": {
                channel: float(np.sum(design.raw_spend[:, index]))
                for index, channel in enumerate(design.channel_names)
            },
            "posterior_intervals": intervals,
            "model_fit_series": model_fit_series,
            "channel_efficiency": efficiency,
            "channel_efficiency_metric": efficiency_metric,
            "budget_response_curves": curves,
            "scenario_plan": (
                self._scenario_plan(design=design, roas=efficiency)
                if recommendations_allowed
                else []
            ),
            "convergence": {
                "max_r_hat": posterior.max_r_hat,
                "min_effective_sample_size": posterior.min_effective_sample_size,
                "divergences": posterior.divergences,
            },
            "seasonality": {
                "period": estimator_input.seasonality_period,
                "terms": ["sine", "cosine"],
            },
            "model_specification": {
                "family": "Bayesian additive media mix",
                "adstock": dict(estimator_input.adstock_decay),
                "saturation": "Hill half-spend curve",
                "control_columns": list(design.control_names),
            },
            "warnings": warnings,
            "plain_language_conclusion": conclusion,
            "sample_counts": {
                "periods": len(design.outcomes),
                "channels": len(design.channel_names),
            },
        }
        if estimator_input.outcome_kind == "revenue":
            diagnostics["channel_roas"] = efficiency

        return AnalysisEstimationResult(
            effect=effect,
            standard_error=standard_error,
            p_value=0.025 if effect_low > 0 else 0.5,
            confidence_interval_low=min(effect_low, effect),
            confidence_interval_high=max(effect_high, effect),
            observation_count=len(design.outcomes),
            library_name=posterior.library_name,
            library_version=posterior.library_version,
            diagnostics=diagnostics,
            incremental_outcome=total,
            relative_lift=(total / float(np.sum(design.outcomes))),
            incremental_revenue=(total if estimator_input.outcome_kind == "revenue" else None),
            incremental_conversions=(
                total if estimator_input.outcome_kind == "conversions" else None
            ),
        )

    @staticmethod
    def _response_curve(
        *, coefficient: float, average_spend: float, half_spend: float
    ) -> list[dict[str, float]]:
        return [
            {
                "spend_multiplier": multiplier,
                "expected_contribution": coefficient
                * (average_spend * multiplier)
                / max(average_spend * multiplier + half_spend, 1e-9),
            }
            for multiplier in (0.5, 0.75, 1.0, 1.25, 1.5)
        ]

    @staticmethod
    def _scenario_plan(
        *, design: MarketingMixDesign, roas: dict[str, float | None]
    ) -> list[dict[str, object]]:
        def ranking_value(channel: str) -> float:
            value = roas[channel]
            return value if value is not None else -math.inf

        ranked = sorted(
            design.channel_names,
            key=ranking_value,
            reverse=True,
        )
        total_budget = float(np.sum(design.raw_spend))
        if not ranked or total_budget <= 0:
            return []
        return [
            {
                "scenario": "Reallocate 10% toward the strongest marginal channel",
                "recommended_channel": ranked[0],
                "budget_to_reallocate": total_budget * 0.10,
                "guardrail": "Validate with a controlled geo or holdout experiment.",
            }
        ]
