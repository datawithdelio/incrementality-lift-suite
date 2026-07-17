from collections.abc import Callable

from incrementality_api.domain.analysis_runs.statistical_library_versions import (
    StatisticalLibraryVersions,
)
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
from incrementality_api.infrastructure.estimation.package_versions import (
    installed_distribution_version,
)
from incrementality_api.infrastructure.estimation.synthetic_control import (
    ScipySyntheticControlEstimator,
)

_ESTIMATOR_PACKAGES: dict[AnalysisEstimatorType, tuple[str, ...]] = {
    AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES: (
        StatsmodelsDifferenceInDifferencesEstimator.statistical_packages
    ),
    AnalysisEstimatorType.SYNTHETIC_CONTROL: (
        ScipySyntheticControlEstimator.statistical_packages
    ),
    AnalysisEstimatorType.GEO_HOLDOUT: (
        StatsmodelsGeoHoldoutEstimator.statistical_packages
    ),
    AnalysisEstimatorType.MARKETING_MIX_MODEL: (
        BayesianMarketingMixEstimator.statistical_packages
    ),
    AnalysisEstimatorType.OFF_POLICY_EVALUATION: (
        StatsmodelsOffPolicyEstimator.statistical_packages
    ),
}


class StatisticalRuntimeVersionProvider:
    """Discover only package versions relevant to each estimator adapter."""

    def __init__(
        self,
        version_reader: Callable[[str], str] = installed_distribution_version,
    ) -> None:
        self._version_reader = version_reader

    def for_estimator(
        self,
        estimator_type: AnalysisEstimatorType,
    ) -> StatisticalLibraryVersions:
        return StatisticalLibraryVersions.from_mapping(
            {
                package_name: self._version_reader(package_name)
                for package_name in _ESTIMATOR_PACKAGES[estimator_type]
            }
        )
