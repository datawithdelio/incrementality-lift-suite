from datetime import UTC, datetime
from uuid import uuid4

from incrementality_api.application.measurement.views import (
    AnalysisSummaryRecord,
    ChannelRecommendationPolicy,
    GetChannelPerformance,
    GetResultsDashboard,
    MeasurementFilters,
)


class FakeRepository:
    def __init__(self, records: tuple[AnalysisSummaryRecord, ...]) -> None:
        self.records = records
        self.filters: MeasurementFilters | None = None

    async def list(self, filters: MeasurementFilters) -> tuple[AnalysisSummaryRecord, ...]:
        self.filters = filters
        return self.records


def record(**changes: object) -> AnalysisSummaryRecord:
    values = {
        "run_id": uuid4(),
        "workspace_id": uuid4(),
        "project_id": uuid4(),
        "project_name": "Acquisition",
        "status": "succeeded",
        "estimator_type": "difference_in_differences",
        "created_at": datetime(2026, 7, 1, tzinfo=UTC),
        "effect": 4.2,
        "confidence_low": 2.0,
        "confidence_high": 6.4,
        "incremental_revenue": 1200.0,
        "incremental_conversions": None,
        "relative_lift": 0.12,
        "diagnostics": {"design_assessment": "valid", "warnings": []},
        "configuration": {"channel": "Paid Search", "spend": 500.0, "observed_roas": 3.0},
        "failure_reason": None,
    }
    values.update(changes)
    return AnalysisSummaryRecord(**values)  # type: ignore[arg-type]


async def test_dashboard_preserves_method_specific_metric_labels() -> None:
    workspace_id = uuid4()
    repository = FakeRepository(
        (
            record(workspace_id=workspace_id),
            record(
                workspace_id=workspace_id,
                estimator_type="marketing_mix_model",
                effect=8.0,
                diagnostics={"design_assessment": "weak", "warnings": ["Low ESS"]},
            ),
            record(workspace_id=workspace_id, status="failed", effect=None),
        )
    )

    view = await GetResultsDashboard(repository).execute(
        MeasurementFilters(workspace_id=workspace_id)
    )

    assert view.total_runs == 3
    assert view.failed_runs == 1
    assert [item.metric_label for item in view.runs[:2]] == [
        "Treatment effect",
        "Modeled outcome contribution",
    ]
    assert view.runs[1].reliability == "weak"


def test_channel_policy_handles_strong_weak_missing_and_conflicting_evidence() -> None:
    policy = ChannelRecommendationPolicy()

    assert (
        policy.recommend(
            incremental_roas=2.4,
            marginal_response=1.2,
            reliability="strong",
            confidence_low=1.0,
            observed_roas=3.0,
        ).movement
        == "increase"
    )
    assert (
        policy.recommend(
            incremental_roas=2.4,
            marginal_response=1.2,
            reliability="weak",
            confidence_low=1.0,
            observed_roas=3.0,
        ).movement
        == "maintain"
    )
    assert (
        policy.recommend(
            incremental_roas=None,
            marginal_response=None,
            reliability="unknown",
            confidence_low=None,
            observed_roas=None,
        ).movement
        == "insufficient_evidence"
    )
    conflicting = policy.recommend(
        incremental_roas=-0.2,
        marginal_response=-0.1,
        reliability="strong",
        confidence_low=-1.0,
        observed_roas=4.0,
    )
    assert conflicting.movement == "reduce"
    assert "observed ROAS" in conflicting.warning


async def test_mmm_conversion_channel_performance_preserves_efficiency_semantics() -> None:
    workspace_id = uuid4()
    repository = FakeRepository(
        (
            record(
                workspace_id=workspace_id,
                estimator_type="marketing_mix_model",
                incremental_revenue=None,
                incremental_conversions=120.0,
                configuration={"outcome_kind": "conversions"},
                diagnostics={
                    "design_assessment": "valid",
                    "warnings": [],
                    "channel_contributions": {
                        "paid_search_spend": 120.0,
                    },
                    "channel_spend": {
                        "paid_search_spend": 600.0,
                    },
                    "posterior_intervals": {
                        "paid_search_spend": {
                            "low": 80.0,
                            "high": 160.0,
                        },
                    },
                    "channel_efficiency": {
                        "paid_search_spend": 0.2,
                    },
                    "channel_efficiency_metric": (
                        "incremental_conversions_per_dollar"
                    ),
                },
            ),
        )
    )

    view = await GetChannelPerformance(repository).execute(
        MeasurementFilters(workspace_id=workspace_id)
    )

    assert len(view.channels) == 1
    channel = view.channels[0]

    assert channel.channel == "paid_search_spend"
    assert channel.incremental_revenue is None
    assert channel.incremental_conversions == 120.0
    assert channel.incremental_roas is None

    assert channel.efficiency == 0.2
    assert (
        channel.efficiency_metric
        == "incremental_conversions_per_dollar"
    )


async def test_channel_performance_uses_incremental_not_observed_roas_for_ranking() -> None:
    workspace_id = uuid4()
    repository = FakeRepository(
        (
            record(workspace_id=workspace_id),
            record(
                workspace_id=workspace_id,
                configuration={"channel": "Social", "spend": 1000.0, "observed_roas": 10.0},
                incremental_revenue=100.0,
                confidence_low=-2.0,
            ),
        )
    )

    view = await GetChannelPerformance(repository).execute(
        MeasurementFilters(workspace_id=workspace_id)
    )

    assert view.channels[0].channel == "Paid Search"
    assert view.channels[0].incremental_roas == 2.4
    assert view.channels[1].observed_roas == 10.0
