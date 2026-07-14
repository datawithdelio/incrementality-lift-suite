from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)


class QueueAnalysisRunRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    dataset_id: UUID
    semantic_mapping_version: int = Field(
        gt=0,
    )
    estimator_type: AnalysisEstimatorType
    estimator_version: str = Field(
        min_length=1,
        max_length=255,
    )
    configuration: dict[str, object]


class AnalysisRunResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    semantic_mapping_id: UUID
    semantic_mapping_version: int
    created_by_user_id: UUID
    estimator_type: AnalysisEstimatorType
    estimator_version: str
    configuration: dict[str, object]
    status: AnalysisRunStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failure_reason: str | None
    cancellation_reason: str | None
