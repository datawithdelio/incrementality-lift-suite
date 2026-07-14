import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Self
from uuid import UUID, uuid4

from incrementality_api.domain.analysis_results.errors import InvalidAnalysisResultError
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    analysis_run_id: UUID
    dataset_id: UUID
    semantic_mapping_id: UUID
    semantic_mapping_version: int
    estimator_type: AnalysisEstimatorType
    estimator_version: str
    library_name: str
    library_version: str
    effect: float
    standard_error: float
    p_value: float
    confidence_interval_low: float
    confidence_interval_high: float
    sample_size: int
    diagnostics_json: str
    incremental_outcome: float | None
    relative_lift: float | None
    incremental_revenue: float | None
    incremental_conversions: float | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
        dataset_id: UUID,
        semantic_mapping_id: UUID,
        semantic_mapping_version: int,
        estimator_type: AnalysisEstimatorType,
        estimator_version: str,
        library_name: str,
        library_version: str,
        effect: float,
        standard_error: float,
        p_value: float,
        confidence_interval_low: float,
        confidence_interval_high: float,
        sample_size: int,
        diagnostics: Mapping[str, object],
        incremental_outcome: float | None,
        relative_lift: float | None,
        incremental_revenue: float | None,
        incremental_conversions: float | None,
        created_at: datetime,
    ) -> Self:
        if semantic_mapping_version <= 0:
            raise InvalidAnalysisResultError("Semantic mapping version must be positive.")
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise InvalidAnalysisResultError("Result creation time must be timezone-aware.")
        normalized_estimator_version = cls._required_text(estimator_version, "Estimator version")
        normalized_library_name = cls._required_text(library_name, "Library name")
        normalized_library_version = cls._required_text(library_version, "Library version")
        for value in (
            effect,
            standard_error,
            p_value,
            confidence_interval_low,
            confidence_interval_high,
        ):
            if not math.isfinite(value):
                raise InvalidAnalysisResultError("Statistical result values must be finite.")
        if standard_error < 0:
            raise InvalidAnalysisResultError("Standard error must be nonnegative.")
        if not 0 <= p_value <= 1:
            raise InvalidAnalysisResultError("P-value must be between zero and one.")
        if not confidence_interval_low <= effect <= confidence_interval_high:
            raise InvalidAnalysisResultError("Confidence interval must contain the effect.")
        if sample_size <= 0:
            raise InvalidAnalysisResultError("Sample size must be positive.")
        business_values = (
            incremental_outcome,
            relative_lift,
            incremental_revenue,
            incremental_conversions,
        )
        if any(value is not None and not math.isfinite(value) for value in business_values):
            raise InvalidAnalysisResultError("Business-impact values must be finite when present.")
        try:
            diagnostics_json = json.dumps(
                dict(diagnostics),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as error:
            raise InvalidAnalysisResultError("Diagnostics must be valid JSON data.") from error
        return cls(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            analysis_run_id=analysis_run_id,
            dataset_id=dataset_id,
            semantic_mapping_id=semantic_mapping_id,
            semantic_mapping_version=semantic_mapping_version,
            estimator_type=estimator_type,
            estimator_version=normalized_estimator_version,
            library_name=normalized_library_name,
            library_version=normalized_library_version,
            effect=effect,
            standard_error=standard_error,
            p_value=p_value,
            confidence_interval_low=confidence_interval_low,
            confidence_interval_high=confidence_interval_high,
            sample_size=sample_size,
            diagnostics_json=diagnostics_json,
            incremental_outcome=incremental_outcome,
            relative_lift=relative_lift,
            incremental_revenue=incremental_revenue,
            incremental_conversions=incremental_conversions,
            created_at=created_at,
        )

    @staticmethod
    def _required_text(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise InvalidAnalysisResultError(f"{field_name} must not be blank.")
        return normalized
