from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)


class RegisterDatasetRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    source_filename: str = Field(
        min_length=1,
        max_length=255,
    )
    media_type: str = Field(
        min_length=1,
        max_length=100,
    )
    byte_size: int = Field(
        gt=0,
    )
    checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
    )


class DatasetResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    workspace_id: UUID
    project_id: UUID
    created_by_user_id: UUID
    source_filename: str
    storage_key: str
    media_type: str
    byte_size: int
    checksum_sha256: str
    status: DatasetStatus
    created_at: datetime
    uploaded_at: datetime | None
    validation_completed_at: datetime | None
    row_count: int | None
    column_count: int | None
    failure_reason: str | None
