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
    estimator_version: str | None = Field(
        default=None,
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



class AnalysisRunLineageResponse(BaseModel):
    analysis_run_id: UUID

    dataset_id: UUID
    dataset_checksum_sha256: str
    dataset_byte_size: int

    semantic_mapping_id: UUID
    semantic_mapping_version: int
    semantic_mapping_snapshot: dict[str, object] | None

    analysis_period_snapshot: dict[str, object] | None
    analysis_selection_snapshot: dict[str, object] | None
    treatment_control_snapshot: dict[str, object] | None
    estimand_snapshot: dict[str, object] | None

    estimator_type: AnalysisEstimatorType
    estimator_version: str
    estimator_configuration: dict[str, object]

    random_seed: int | None
    application_version: str | None
    source_revision: str | None
    statistical_library_versions: dict[str, str] | None

    input_fingerprint_sha256: str | None
    created_at: datetime
