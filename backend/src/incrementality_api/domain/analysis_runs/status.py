from enum import StrEnum


class AnalysisEstimatorType(StrEnum):
    """Supported causal-estimator families."""

    DIFFERENCE_IN_DIFFERENCES = "difference_in_differences"
    SYNTHETIC_CONTROL = "synthetic_control"
    GEO_HOLDOUT = "geo_holdout"
    MARKETING_MIX_MODEL = "marketing_mix_model"
    OFF_POLICY_EVALUATION = "off_policy_evaluation"


class AnalysisRunStatus(StrEnum):
    """Customer-visible analysis execution state."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
