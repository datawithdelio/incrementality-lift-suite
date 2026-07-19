from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
)

_ESTIMATOR_VERSIONS: dict[
    AnalysisEstimatorType,
    str,
] = {
    AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES: "did-v1",
    AnalysisEstimatorType.SYNTHETIC_CONTROL: "synthetic-control-v1",
    AnalysisEstimatorType.GEO_HOLDOUT: "geo-holdout-v1",
    AnalysisEstimatorType.MARKETING_MIX_MODEL: "mmm-v1",
    AnalysisEstimatorType.OFF_POLICY_EVALUATION: "off-policy-v1",
}


def estimator_version_for(
    estimator_type: AnalysisEstimatorType,
) -> str:
    """Return the server-owned implementation version for an estimator."""
    return _ESTIMATOR_VERSIONS[estimator_type]
