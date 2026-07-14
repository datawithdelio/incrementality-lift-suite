import math

import numpy as np
import statsmodels.api as sm  # type: ignore[import-untyped]

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
    DifferenceInDifferencesInput,
    PermanentEstimationError,
)


class StatsmodelsDifferenceInDifferencesEstimator:
    """Estimate a two-period DiD interaction with statsmodels OLS."""

    def estimate(self, estimator_input: object) -> AnalysisEstimationResult:
        if not isinstance(estimator_input, DifferenceInDifferencesInput):
            raise PermanentEstimationError("Difference-in-differences input has an invalid shape.")

        observations = estimator_input.observations
        treated_values = {observation.treated for observation in observations}
        if treated_values != {False, True}:
            raise PermanentEstimationError(
                "Difference-in-differences requires treated and control groups."
            )

        post_values = {observation.post_period for observation in observations}
        if post_values != {False, True}:
            raise PermanentEstimationError(
                "Difference-in-differences requires pre and post periods."
            )

        if len(observations) < 4:
            raise PermanentEstimationError(
                "Difference-in-differences requires at least four observations."
            )

        outcomes = np.asarray(
            [observation.outcome for observation in observations],
            dtype=float,
        )
        if not np.isfinite(outcomes).all():
            raise PermanentEstimationError("Outcome values must be finite.")

        treated = np.asarray(
            [float(observation.treated) for observation in observations],
        )
        post = np.asarray(
            [float(observation.post_period) for observation in observations],
        )
        interaction = treated * post
        design = np.column_stack(
            (
                np.ones(len(observations)),
                treated,
                post,
                interaction,
            )
        )
        groups = np.asarray([observation.unit for observation in observations])

        try:
            fitted = sm.OLS(outcomes, design).fit(
                cov_type="cluster",
                cov_kwds={"groups": groups},
            )
            interval = fitted.conf_int(alpha=0.05)[3]
            result = AnalysisEstimationResult(
                effect=float(fitted.params[3]),
                standard_error=float(fitted.bse[3]),
                p_value=float(fitted.pvalues[3]),
                confidence_interval_low=float(interval[0]),
                confidence_interval_high=float(interval[1]),
                observation_count=len(observations),
                library_name="statsmodels",
                library_version=str(sm.__version__),
                diagnostics={
                    "r_squared": float(fitted.rsquared),
                    "adjusted_r_squared": float(fitted.rsquared_adj),
                    "degrees_of_freedom": float(fitted.df_resid),
                    "covariance_type": str(fitted.cov_type),
                },
            )
        except (ValueError, TypeError, np.linalg.LinAlgError) as error:
            raise PermanentEstimationError(
                "Difference-in-differences estimation failed for the supplied design."
            ) from error

        if not all(
            math.isfinite(value)
            for value in (
                result.effect,
                result.standard_error,
                result.p_value,
                result.confidence_interval_low,
                result.confidence_interval_high,
            )
        ):
            raise PermanentEstimationError(
                "Difference-in-differences produced non-finite statistics."
            )
        return result
