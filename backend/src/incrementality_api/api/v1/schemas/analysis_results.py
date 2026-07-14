from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType, AnalysisRunStatus


class ConfidenceIntervalResponse(BaseModel):
    low: float
    high: float
    confidence_level: float = 0.95


class BusinessImpactResponse(BaseModel):
    incremental_outcome: float | None
    relative_lift: float | None
    incremental_revenue: float | None
    incremental_conversions: float | None


class StatisticalResultResponse(BaseModel):
    effect_estimate: float
    standard_error: float
    confidence_interval: ConfidenceIntervalResponse
    p_value: float
    sample_size: int
    estimator_version: str
    library_name: str
    library_version: str
    technical_diagnostics: dict[str, object]
    business_impact: BusinessImpactResponse
    created_at: datetime


class AnalysisResultResponse(BaseModel):
    analysis_run_id: UUID
    workspace_id: UUID
    project_id: UUID
    run_status: AnalysisRunStatus
    lifecycle_status: Literal[
        "queued", "running", "retrying", "succeeded", "failed", "cancelled"
    ]
    estimator_type: AnalysisEstimatorType
    estimator_version: str
    analysis_configuration: dict[str, object]
    attempt_count: int
    max_attempts: int
    failure_information: str | None
    result: StatisticalResultResponse | None
