from datetime import date

import pytest

from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType


@pytest.mark.parametrize(
    "estimator_type",
    [
        AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        AnalysisEstimatorType.SYNTHETIC_CONTROL,
        AnalysisEstimatorType.GEO_HOLDOUT,
    ],
)
def test_treatment_methods_derive_canonical_pre_and_post_periods(
    estimator_type: AnalysisEstimatorType,
) -> None:
    snapshot = AnalysisPeriodSnapshot.from_configuration(
        estimator_type,
        {
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31T23:59:59+00:00",
            "intervention_date": "2026-01-15T00:00:00Z",
        },
    )

    assert snapshot.analysis_start_date == date(2026, 1, 1)
    assert snapshot.analysis_end_date == date(2026, 1, 31)
    assert snapshot.intervention_date == date(2026, 1, 15)
    assert snapshot.pre_period_start_date == date(2026, 1, 1)
    assert snapshot.pre_period_end_date == date(2026, 1, 14)
    assert snapshot.post_period_start_date == date(2026, 1, 15)
    assert snapshot.post_period_end_date == date(2026, 1, 31)


def test_mmm_supports_an_optional_validation_window_without_intervention() -> None:
    snapshot = AnalysisPeriodSnapshot.from_configuration(
        AnalysisEstimatorType.MARKETING_MIX_MODEL,
        {
            "analysis_start_date": "2025-01-01",
            "analysis_end_date": "2025-12-31",
            "validation_start_date": "2025-10-01",
            "validation_end_date": "2025-12-31",
        },
    )

    assert snapshot.intervention_date is None
    assert snapshot.validation_start_date == date(2025, 10, 1)
    assert snapshot.validation_end_date == date(2025, 12, 31)


def test_off_policy_supports_an_optional_intervention_date() -> None:
    without_intervention = AnalysisPeriodSnapshot.from_configuration(
        AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        {"analysis_start_date": "2026-01-01", "analysis_end_date": "2026-01-31"},
    )
    with_intervention = AnalysisPeriodSnapshot.from_configuration(
        AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        {
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31",
            "intervention_date": "2026-01-20",
        },
    )

    assert without_intervention.intervention_date is None
    assert with_intervention.intervention_date == date(2026, 1, 20)


@pytest.mark.parametrize(
    ("estimator_type", "configuration", "message"),
    [
        (AnalysisEstimatorType.MARKETING_MIX_MODEL, {}, "analysis_start_date"),
        (
            AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
            {"analysis_start_date": "2026-01-01", "analysis_end_date": "2026-01-31"},
            "intervention_date",
        ),
        (
            AnalysisEstimatorType.MARKETING_MIX_MODEL,
            {"analysis_start_date": "2026-02-01", "analysis_end_date": "2026-01-31"},
            "must not follow",
        ),
        (
            AnalysisEstimatorType.GEO_HOLDOUT,
            {
                "analysis_start_date": "2026-01-10",
                "analysis_end_date": "2026-01-31",
                "intervention_date": "2026-01-01",
            },
            "inside",
        ),
        (
            AnalysisEstimatorType.SYNTHETIC_CONTROL,
            {
                "analysis_start_date": "2026-01-01",
                "analysis_end_date": "2026-01-31",
                "intervention_date": "2026-01-15",
                "pre_period_start_date": "2026-01-01",
                "pre_period_end_date": "2026-01-15",
                "post_period_start_date": "2026-01-15",
                "post_period_end_date": "2026-01-31",
            },
            "before the intervention",
        ),
        (
            AnalysisEstimatorType.MARKETING_MIX_MODEL,
            {
                "analysis_start_date": "2026-01-01",
                "analysis_end_date": "2026-01-31",
                "validation_start_date": "2026-01-20",
            },
            "together",
        ),
        (
            AnalysisEstimatorType.OFF_POLICY_EVALUATION,
            {
                "analysis_start_date": "2026-01-01T00:00:00",
                "analysis_end_date": "2026-01-31",
            },
            "timezone-aware",
        ),
    ],
)
def test_invalid_estimator_periods_are_rejected(
    estimator_type: AnalysisEstimatorType,
    configuration: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(InvalidAnalysisRunError, match=message):
        AnalysisPeriodSnapshot.from_configuration(estimator_type, configuration)


def test_canonical_json_round_trips() -> None:
    snapshot = AnalysisPeriodSnapshot.from_configuration(
        AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        {
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31",
            "intervention_date": "2026-01-15",
        },
    )

    assert AnalysisPeriodSnapshot.from_json(snapshot.canonical_json) == snapshot
