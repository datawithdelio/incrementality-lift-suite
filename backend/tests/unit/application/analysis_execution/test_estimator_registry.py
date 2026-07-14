import pytest

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
    AnalysisEstimatorRegistry,
    UnsupportedEstimatorTypeError,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType


class FakeEstimator:
    def estimate(self, estimator_input: object) -> AnalysisEstimationResult:
        del estimator_input
        raise AssertionError("Selection must not execute the estimator.")


def test_selects_registered_estimator_adapter() -> None:
    estimator = FakeEstimator()
    registry = AnalysisEstimatorRegistry(
        {AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES: estimator}
    )

    selected = registry.select(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES)

    assert selected is estimator


def test_rejects_unsupported_estimator_type() -> None:
    registry = AnalysisEstimatorRegistry({})

    with pytest.raises(UnsupportedEstimatorTypeError, match="synthetic_control"):
        registry.select(AnalysisEstimatorType.SYNTHETIC_CONTROL)
