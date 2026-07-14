from dataclasses import dataclass
from typing import Protocol

from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType


class EstimationError(Exception):
    """Base error raised while preparing or executing an estimator."""


class RetryableEstimationError(EstimationError):
    """A transient estimation failure that may succeed on a later attempt."""


class PermanentEstimationError(EstimationError):
    """An invalid or unsupported analysis that must not be retried."""


class UnsupportedEstimatorTypeError(PermanentEstimationError):
    """No registered adapter can execute the requested estimator family."""


@dataclass(frozen=True, slots=True)
class DifferenceInDifferencesObservation:
    unit: str
    outcome: float
    treated: bool
    post_period: bool


@dataclass(frozen=True, slots=True)
class DifferenceInDifferencesInput:
    observations: tuple[DifferenceInDifferencesObservation, ...]


@dataclass(frozen=True, slots=True)
class AnalysisEstimatorInput:
    estimator_type: AnalysisEstimatorType
    payload: object


@dataclass(frozen=True, slots=True)
class AnalysisEstimationResult:
    effect: float
    standard_error: float
    p_value: float
    confidence_interval_low: float
    confidence_interval_high: float
    observation_count: int


class AnalysisEstimator(Protocol):
    def estimate(self, estimator_input: object) -> AnalysisEstimationResult:
        """Execute CPU-bound statistical estimation synchronously."""


class AnalysisEstimatorSelector(Protocol):
    def select(self, estimator_type: AnalysisEstimatorType) -> AnalysisEstimator:
        """Return the adapter registered for an estimator family."""


class AnalysisEstimatorRegistry:
    """Select estimator adapters without coupling the worker to libraries."""

    def __init__(self, estimators: dict[AnalysisEstimatorType, AnalysisEstimator]) -> None:
        self._estimators = dict(estimators)

    def select(self, estimator_type: AnalysisEstimatorType) -> AnalysisEstimator:
        estimator = self._estimators.get(estimator_type)
        if estimator is None:
            raise UnsupportedEstimatorTypeError(
                f"Estimator type '{estimator_type.value}' is unsupported."
            )
        return estimator
