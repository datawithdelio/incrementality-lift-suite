from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MeasurementFilters:
    workspace_id: UUID
    project_id: UUID | None = None
    estimator_type: str | None = None
    status: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class AnalysisSummaryRecord:
    run_id: UUID
    workspace_id: UUID
    project_id: UUID
    project_name: str
    status: str
    estimator_type: str
    created_at: datetime
    effect: float | None
    confidence_low: float | None
    confidence_high: float | None
    incremental_revenue: float | None
    incremental_conversions: float | None
    relative_lift: float | None
    diagnostics: Mapping[str, object]
    configuration: Mapping[str, object]
    failure_reason: str | None


class MeasurementRepository(Protocol):
    async def list(self, filters: MeasurementFilters) -> tuple[AnalysisSummaryRecord, ...]: ...


_METRIC_LABELS = {
    "difference_in_differences": "Treatment effect",
    "synthetic_control": "Synthetic-control gap",
    "geo_holdout": "Geographic lift",
    "marketing_mix_model": "Modeled outcome contribution",
    "off_policy_evaluation": "Estimated policy value",
}


@dataclass(frozen=True, slots=True)
class DashboardRun:
    run_id: UUID
    project_id: UUID
    project_name: str
    status: str
    estimator_type: str
    method_label: str
    metric_label: str
    effect: float | None
    confidence_low: float | None
    confidence_high: float | None
    reliability: str
    business_impact: float | None
    warnings: tuple[str, ...]
    created_at: datetime
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class ResultsDashboardView:
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    active_runs: int
    runs: tuple[DashboardRun, ...]


def _warnings(diagnostics: Mapping[str, object]) -> tuple[str, ...]:
    raw = diagnostics.get("warnings", diagnostics.get("diagnostic_warnings", ()))
    if not isinstance(raw, list | tuple):
        return ()
    return tuple(str(item) for item in raw)


def _reliability(diagnostics: Mapping[str, object]) -> str:
    value = diagnostics.get("reliability", diagnostics.get("design_assessment", "unknown"))
    return str(value)


class GetResultsDashboard:
    def __init__(self, repository: MeasurementRepository) -> None:
        self._repository = repository

    async def execute(self, filters: MeasurementFilters) -> ResultsDashboardView:
        records = await self._repository.list(filters)
        runs = tuple(
            DashboardRun(
                run_id=item.run_id,
                project_id=item.project_id,
                project_name=item.project_name,
                status=item.status,
                estimator_type=item.estimator_type,
                method_label=item.estimator_type.replace("_", " ").title(),
                metric_label=_METRIC_LABELS.get(item.estimator_type, "Method-specific estimate"),
                effect=item.effect,
                confidence_low=item.confidence_low,
                confidence_high=item.confidence_high,
                reliability=_reliability(item.diagnostics),
                business_impact=(item.incremental_revenue or item.incremental_conversions),
                warnings=_warnings(item.diagnostics),
                created_at=item.created_at,
                failure_reason=item.failure_reason,
            )
            for item in records
        )
        return ResultsDashboardView(
            total_runs=len(runs),
            succeeded_runs=sum(item.status == "succeeded" for item in runs),
            failed_runs=sum(item.status == "failed" for item in runs),
            active_runs=sum(item.status in {"queued", "running"} for item in runs),
            runs=runs,
        )


@dataclass(frozen=True, slots=True)
class Recommendation:
    movement: str
    warning: str


class ChannelRecommendationPolicy:
    """Turn incremental evidence into cautious budget guidance."""

    def recommend(
        self,
        *,
        incremental_roas: float | None,
        marginal_response: float | None,
        reliability: str,
        confidence_low: float | None,
        observed_roas: float | None,
    ) -> Recommendation:
        if incremental_roas is None or confidence_low is None:
            return Recommendation("insufficient_evidence", "More causal evidence is required.")
        if reliability not in {"strong", "valid"}:
            return Recommendation("maintain", "Reliability is too weak for budget movement.")
        conflict = observed_roas is not None and observed_roas > 1 and incremental_roas <= 0
        if incremental_roas <= 0 or confidence_low < 0:
            warning = (
                "The observed ROAS conflicts with incremental evidence."
                if conflict
                else "Incremental evidence supports reducing exposure."
            )
            return Recommendation("reduce", warning)
        if incremental_roas > 1 and (marginal_response or 0) > 0:
            return Recommendation(
                "increase", "Strong incremental evidence supports a measured increase."
            )
        return Recommendation("maintain", "Current evidence supports maintaining budget.")


@dataclass(frozen=True, slots=True)
class ChannelPerformanceItem:
    channel: str
    spend: float | None
    incremental_revenue: float | None
    incremental_conversions: float | None
    lift: float | None
    incremental_roas: float | None
    observed_roas: float | None
    confidence_low: float | None
    confidence_high: float | None
    contribution: float | None
    marginal_response: float | None
    reliability: str
    recommended_movement: str
    warning: str


@dataclass(frozen=True, slots=True)
class ChannelPerformanceView:
    channels: tuple[ChannelPerformanceItem, ...]


class GetChannelPerformance:
    def __init__(
        self, repository: MeasurementRepository, policy: ChannelRecommendationPolicy | None = None
    ) -> None:
        self._repository = repository
        self._policy = policy or ChannelRecommendationPolicy()

    async def execute(self, filters: MeasurementFilters) -> ChannelPerformanceView:
        records = await self._repository.list(filters)
        channels: list[ChannelPerformanceItem] = []
        for item in records:
            contributions = item.diagnostics.get("channel_contributions")
            roas = item.diagnostics.get("channel_roas")
            spends = item.diagnostics.get("channel_spend")
            intervals = item.diagnostics.get("posterior_intervals")
            if (
                isinstance(contributions, Mapping)
                and isinstance(roas, Mapping)
                and isinstance(spends, Mapping)
            ):
                for channel_name, contribution_value in contributions.items():
                    if not isinstance(channel_name, str) or not isinstance(
                        contribution_value, int | float
                    ):
                        continue
                    roas_value = roas.get(channel_name)
                    spend_value = spends.get(channel_name)
                    interval = (
                        intervals.get(channel_name) if isinstance(intervals, Mapping) else None
                    )
                    low_value = interval.get("low") if isinstance(interval, Mapping) else None
                    high_value = interval.get("high") if isinstance(interval, Mapping) else None
                    incremental_roas = (
                        float(roas_value) if isinstance(roas_value, int | float) else None
                    )
                    spend = float(spend_value) if isinstance(spend_value, int | float) else None
                    confidence_low = (
                        float(low_value) if isinstance(low_value, int | float) else None
                    )
                    confidence_high = (
                        float(high_value) if isinstance(high_value, int | float) else None
                    )
                    reliability = _reliability(item.diagnostics)
                    recommendation = self._policy.recommend(
                        incremental_roas=incremental_roas,
                        marginal_response=incremental_roas,
                        reliability=reliability,
                        confidence_low=confidence_low,
                        observed_roas=None,
                    )
                    channels.append(
                        ChannelPerformanceItem(
                            channel=channel_name,
                            spend=spend,
                            incremental_revenue=float(contribution_value),
                            incremental_conversions=None,
                            lift=item.relative_lift,
                            incremental_roas=incremental_roas,
                            observed_roas=None,
                            confidence_low=confidence_low,
                            confidence_high=confidence_high,
                            contribution=float(contribution_value),
                            marginal_response=incremental_roas,
                            reliability=reliability,
                            recommended_movement=recommendation.movement,
                            warning=recommendation.warning,
                        )
                    )
                continue
            channel = item.configuration.get("channel")
            if not isinstance(channel, str):
                continue
            spend_value = item.configuration.get("spend")
            spend = float(spend_value) if isinstance(spend_value, int | float) else None
            observed_value = item.configuration.get("observed_roas")
            observed = float(observed_value) if isinstance(observed_value, int | float) else None
            incremental_roas = (
                item.incremental_revenue / spend
                if item.incremental_revenue is not None and spend is not None and spend != 0
                else None
            )
            marginal_value = item.diagnostics.get("marginal_response")
            marginal = (
                float(marginal_value)
                if isinstance(marginal_value, int | float)
                else incremental_roas
            )
            reliability = _reliability(item.diagnostics)
            recommendation = self._policy.recommend(
                incremental_roas=incremental_roas,
                marginal_response=marginal,
                reliability=reliability,
                confidence_low=item.confidence_low,
                observed_roas=observed,
            )
            contribution_value = item.diagnostics.get("channel_contribution")
            contribution = (
                float(contribution_value) if isinstance(contribution_value, int | float) else None
            )
            channels.append(
                ChannelPerformanceItem(
                    channel=channel,
                    spend=spend,
                    incremental_revenue=item.incremental_revenue,
                    incremental_conversions=item.incremental_conversions,
                    lift=item.relative_lift,
                    incremental_roas=incremental_roas,
                    observed_roas=observed,
                    confidence_low=item.confidence_low,
                    confidence_high=item.confidence_high,
                    contribution=contribution,
                    marginal_response=marginal,
                    reliability=reliability,
                    recommended_movement=recommendation.movement,
                    warning=recommendation.warning,
                )
            )
        channels.sort(key=lambda item: item.incremental_roas or float("-inf"), reverse=True)
        return ChannelPerformanceView(tuple(channels))
