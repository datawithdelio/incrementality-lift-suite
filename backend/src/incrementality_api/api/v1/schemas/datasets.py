from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from incrementality_api.domain.datasets.columns import (
    DatasetColumnType,
)
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
    validation_started_at: datetime | None
    validation_completed_at: datetime | None
    row_count: int | None
    column_count: int | None
    failure_reason: str | None


class DatasetColumnResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    ordinal_position: int
    source_name: str
    normalized_name: str
    inferred_type: DatasetColumnType
    nullable: bool
    missing_count: int


class CreateDatasetSemanticMappingRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    time_column: str = Field(
        min_length=1,
        max_length=255,
    )
    unit_column: str = Field(
        min_length=1,
        max_length=255,
    )
    treatment_column: str = Field(
        min_length=1,
        max_length=255,
    )
    outcome_column: str = Field(
        min_length=1,
        max_length=255,
    )
    spend_column: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    covariate_columns: tuple[str, ...] = ()
    treatment_value: str = Field(
        min_length=1,
        max_length=255,
    )
    control_value: str = Field(
        min_length=1,
        max_length=255,
    )


class DatasetSemanticMappingResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    dataset_id: UUID
    created_by_user_id: UUID
    version: int
    time_column: str
    unit_column: str
    treatment_column: str
    outcome_column: str
    spend_column: str | None
    covariate_columns: tuple[str, ...]
    treatment_value: str
    control_value: str
    created_at: datetime
    updated_at: datetime
