from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


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


class TrendPointResponse(BaseModel):
    period: str
    treatment_value: float | None
    control_value: float | None
    treatment_observations: int
    control_observations: int
    phase: str


class HistogramBinResponse(BaseModel):
    minimum: float
    maximum: float
    treatment_count: int
    control_count: int


class OutcomeDistributionResponse(BaseModel):
    minimum: float | None
    maximum: float | None
    mean: float | None
    median: float | None
    first_quartile: float | None
    third_quartile: float | None
    outlier_count: int
    sample_size: int
    bins: tuple[HistogramBinResponse, ...]


class MissingnessPointResponse(BaseModel):
    column: str
    missing_count: int
    missing_percentage: float


class TreatmentBalanceResponse(BaseModel):
    treatment_label: str
    treatment_value: str
    treatment_count: int
    treatment_percentage: float
    control_label: str
    control_value: str
    control_count: int
    control_percentage: float
    treatment_pre_count: int
    treatment_post_count: int
    control_pre_count: int
    control_post_count: int
    status: str


class BreakdownPointResponse(BaseModel):
    value: str
    outcome_mean: float | None
    observation_count: int
    treatment_count: int
    control_count: int


class DatasetVisualizationsResponse(BaseModel):
    time_column: str | None
    treatment_column: str | None
    outcome_column: str | None
    treatment_start_date: str | None
    trend: tuple[TrendPointResponse, ...]
    distribution: OutcomeDistributionResponse
    missingness: tuple[MissingnessPointResponse, ...]
    balance: TreatmentBalanceResponse | None
    breakdowns: dict[str, tuple[BreakdownPointResponse, ...]]


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
    visualizations: DatasetVisualizationsResponse


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
    failure_reason: str | None
    created_at: datetime

    @field_validator(
        "failure_reason",
        mode="before",
    )
    @classmethod
    def sanitize_failure_reason(
        cls,
        value: object,
    ) -> str | None:
        if value is None:
            return None

        return (
            "Report generation failed. "
            "Please regenerate the report."
        )
