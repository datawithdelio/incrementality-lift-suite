from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
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
    observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DifferenceInDifferencesInput:
    observations: tuple[DifferenceInDifferencesObservation, ...]


@dataclass(frozen=True, slots=True)
class PanelObservation:
    unit: str
    observed_at: datetime
    outcome: float
    treated: bool
    post_period: bool


@dataclass(frozen=True, slots=True)
class SyntheticControlInput:
    observations: tuple[PanelObservation, ...]


@dataclass(frozen=True, slots=True)
class GeoCoordinate:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class GeoHoldoutInput:
    observations: tuple[PanelObservation, ...]
    coordinates: Mapping[str, GeoCoordinate]
    outcome_kind: str
    spillover_pairs: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class MarketingMixObservation:
    observed_at: datetime
    outcome: float
    channel_spend: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class MarketingMixInput:
    observations: tuple[MarketingMixObservation, ...]
    adstock_decay: Mapping[str, float]
    saturation_half_spend: Mapping[str, float]
    seasonality_period: int
    outcome_kind: str


@dataclass(frozen=True, slots=True)
class PolicyEvaluationObservation:
    reward: float
    behavior_probability: float
    target_probability: float
    expected_reward: float


@dataclass(frozen=True, slots=True)
class OffPolicyEvaluationInput:
    observations: tuple[PolicyEvaluationObservation, ...]
    policy_name: str
    primary_method: str = "doubly_robust"


@dataclass(frozen=True, slots=True)
class AnalysisEstimatorInput:
    estimator_type: AnalysisEstimatorType
    random_seed: int
    payload: object


@dataclass(frozen=True, slots=True)
class AnalysisEstimationResult:
    effect: float
    standard_error: float
    p_value: float
    confidence_interval_low: float
    confidence_interval_high: float
    observation_count: int
    library_name: str = "unknown"
    library_version: str = "unknown"
    diagnostics: Mapping[str, object] = field(default_factory=dict)
    incremental_outcome: float | None = None
    relative_lift: float | None = None
    incremental_revenue: float | None = None
    incremental_conversions: float | None = None


class AnalysisEstimator(Protocol):
    def estimate(
        self,
        estimator_input: object,
        *,
        random_seed: int,
    ) -> AnalysisEstimationResult:
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
