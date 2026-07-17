import pytest

from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.infrastructure.estimation.difference_in_differences import (
    StatsmodelsDifferenceInDifferencesEstimator,
)
from incrementality_api.infrastructure.estimation.geo_holdout import (
    StatsmodelsGeoHoldoutEstimator,
)
from incrementality_api.infrastructure.estimation.marketing_mix_model import (
    BayesianMarketingMixEstimator,
)
from incrementality_api.infrastructure.estimation.off_policy_evaluation import (
    StatsmodelsOffPolicyEstimator,
)
from incrementality_api.infrastructure.estimation.runtime_versions import (
    StatisticalRuntimeVersionProvider,
)
from incrementality_api.infrastructure.estimation.synthetic_control import (
    ScipySyntheticControlEstimator,
)

EXPECTED_PACKAGES = {
    AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES: {
        "numpy",
        "statsmodels",
    },
    AnalysisEstimatorType.SYNTHETIC_CONTROL: {
        "numpy",
        "scipy",
    },
    AnalysisEstimatorType.GEO_HOLDOUT: {
        "numpy",
        "statsmodels",
    },
    AnalysisEstimatorType.MARKETING_MIX_MODEL: {
        "arviz",
        "numpy",
        "pymc",
        "pytensor",
    },
    AnalysisEstimatorType.OFF_POLICY_EVALUATION: {
        "numpy",
        "scipy",
    },
}

ESTIMATOR_ADAPTERS = {
    AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES: (
        StatsmodelsDifferenceInDifferencesEstimator
    ),
    AnalysisEstimatorType.SYNTHETIC_CONTROL: ScipySyntheticControlEstimator,
    AnalysisEstimatorType.GEO_HOLDOUT: StatsmodelsGeoHoldoutEstimator,
    AnalysisEstimatorType.MARKETING_MIX_MODEL: BayesianMarketingMixEstimator,
    AnalysisEstimatorType.OFF_POLICY_EVALUATION: StatsmodelsOffPolicyEstimator,
}


@pytest.mark.parametrize("estimator_type", list(AnalysisEstimatorType))
def test_every_estimator_adapter_declares_its_statistical_packages(
    estimator_type: AnalysisEstimatorType,
) -> None:
    assert set(ESTIMATOR_ADAPTERS[estimator_type].statistical_packages) == (
        EXPECTED_PACKAGES[estimator_type]
    )


@pytest.mark.parametrize("estimator_type", list(AnalysisEstimatorType))
def test_discovers_relevant_versions_for_every_supported_estimator(
    estimator_type: AnalysisEstimatorType,
) -> None:
    requested_packages: list[str] = []

    def read_version(package_name: str) -> str:
        requested_packages.append(package_name)
        return f"installed-{package_name}"

    provider = StatisticalRuntimeVersionProvider(version_reader=read_version)

    snapshot = provider.for_estimator(estimator_type)

    assert set(requested_packages) == EXPECTED_PACKAGES[estimator_type]
    assert snapshot.as_dict() == {
        package_name: f"installed-{package_name}"
        for package_name in sorted(EXPECTED_PACKAGES[estimator_type])
    }


@pytest.mark.parametrize("estimator_type", list(AnalysisEstimatorType))
def test_required_runtime_distributions_are_installed(
    estimator_type: AnalysisEstimatorType,
) -> None:
    snapshot = StatisticalRuntimeVersionProvider().for_estimator(estimator_type)

    assert set(snapshot.as_dict()) == EXPECTED_PACKAGES[estimator_type]
    assert all(version.strip() for version in snapshot.as_dict().values())
