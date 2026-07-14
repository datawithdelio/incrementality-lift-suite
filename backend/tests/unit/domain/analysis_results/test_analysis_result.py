from datetime import UTC, datetime
from uuid import uuid4

import pytest

from incrementality_api.domain.analysis_results.entities import AnalysisResult
from incrementality_api.domain.analysis_results.errors import InvalidAnalysisResultError
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

CREATED_AT = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


def build_result(**overrides: object) -> AnalysisResult:
    arguments: dict[str, object] = {
        "workspace_id": uuid4(),
        "project_id": uuid4(),
        "analysis_run_id": uuid4(),
        "dataset_id": uuid4(),
        "semantic_mapping_id": uuid4(),
        "semantic_mapping_version": 2,
        "estimator_type": AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        "estimator_version": "did-v1",
        "library_name": "statsmodels",
        "library_version": "0.14.6",
        "effect": 5.0,
        "standard_error": 0.5,
        "p_value": 0.01,
        "confidence_interval_low": 4.0,
        "confidence_interval_high": 6.0,
        "sample_size": 100,
        "diagnostics": {"r_squared": 0.92, "covariance_type": "cluster"},
        "incremental_outcome": 500.0,
        "relative_lift": 0.12,
        "incremental_revenue": 1000.0,
        "incremental_conversions": 25.0,
        "created_at": CREATED_AT,
    }
    arguments.update(overrides)
    return AnalysisResult.create(**arguments)  # type: ignore[arg-type]


def test_creates_structured_canonical_analysis_result() -> None:
    result = build_result()

    assert result.effect == 5.0
    assert result.sample_size == 100
    assert result.diagnostics_json == '{"covariance_type":"cluster","r_squared":0.92}'
    assert result.incremental_revenue == 1000.0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("effect", float("nan"), "finite"),
        ("standard_error", -0.1, "nonnegative"),
        ("p_value", 2.0, "between zero and one"),
        ("confidence_interval_low", 5.5, "contain the effect"),
        ("sample_size", 0, "positive"),
    ],
)
def test_rejects_invalid_statistical_result(
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(InvalidAnalysisResultError, match=message):
        build_result(**{field: value})


def test_requires_timezone_aware_creation_time() -> None:
    with pytest.raises(InvalidAnalysisResultError, match="timezone-aware"):
        build_result(created_at=CREATED_AT.replace(tzinfo=None))
