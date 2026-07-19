import pytest

from incrementality_api.domain.analysis_runs.estimator_versions import (
    estimator_version_for,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
)


@pytest.mark.parametrize(
    ("estimator_type", "expected"),
    [
        (
            AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
            "did-v1",
        ),
        (
            AnalysisEstimatorType.SYNTHETIC_CONTROL,
            "synthetic-control-v1",
        ),
        (
            AnalysisEstimatorType.GEO_HOLDOUT,
            "geo-holdout-v1",
        ),
        (
            AnalysisEstimatorType.MARKETING_MIX_MODEL,
            "mmm-v1",
        ),
        (
            AnalysisEstimatorType.OFF_POLICY_EVALUATION,
            "off-policy-v1",
        ),
    ],
)
def test_estimator_version_is_owned_by_server(
    estimator_type: AnalysisEstimatorType,
    expected: str,
) -> None:
    assert (
        estimator_version_for(
            estimator_type,
        )
        == expected
    )
