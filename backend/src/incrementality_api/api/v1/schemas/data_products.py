from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ColumnSummaryResponse(BaseModel):
    name: str
    inferred_type: str
    missing_percentage: float
    unique_count: int
    minimum: float | str | None
    maximum: float | str | None
    mean: float | None
    median: float | None


class DateRangeResponse(BaseModel):
    column: str
    minimum: str
    maximum: str


class DatasetPreviewResponse(BaseModel):
    rows: tuple[dict[str, str], ...]
    columns: tuple[ColumnSummaryResponse, ...]
    total_rows: int
    page: int
    page_size: int
    total_pages: int
    date_range: DateRangeResponse | None
    treatment_distribution: dict[str, int]
    outcome_distribution: dict[str, float]


class DatasetVersionResponse(BaseModel):
    id: UUID
    source_filename: str
    checksum_sha256: str
    row_count: int | None
    created_at: datetime


class QualityFindingResponse(BaseModel):
    rule_id: str
    severity: str
    passed: bool
    evidence: dict[str, object]
    recommendation: str


class DataQualityResponse(BaseModel):
    score: int
    ready: bool
    findings: tuple[QualityFindingResponse, ...]


class QueueReportRequest(BaseModel):
    format: str


class ReportJobResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    analysis_run_id: UUID
    version: int
    format: str
    status: str
    attempt_count: int
    max_attempts: int
    storage_key: str | None
    failure_reason: str | None
    created_at: datetime
