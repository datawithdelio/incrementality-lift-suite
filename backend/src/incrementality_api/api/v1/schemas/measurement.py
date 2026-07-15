from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DashboardRunResponse(BaseModel):
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


class ResultsDashboardResponse(BaseModel):
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    active_runs: int
    runs: tuple[DashboardRunResponse, ...]


class ChannelPerformanceResponse(BaseModel):
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


class ChannelPerformanceListResponse(BaseModel):
    channels: tuple[ChannelPerformanceResponse, ...]
