from datetime import UTC, datetime, timedelta

import pytest

from incrementality_api.application.analysis_execution.estimation import (
    GeoCoordinate,
    GeoHoldoutInput,
    PanelObservation,
)
from incrementality_api.infrastructure.estimation.geo_holdout import (
    StatsmodelsGeoHoldoutEstimator,
)


def geo_panel(*, units: int = 12, pretrend: float = 0.0) -> GeoHoldoutInput:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    observations: list[PanelObservation] = []
    coordinates: dict[str, GeoCoordinate] = {}
    for unit_index in range(units):
        treated = unit_index >= units // 2
        unit = f"geo-{unit_index}"
        coordinates[unit] = GeoCoordinate(30 + unit_index, -100 + unit_index)
        for period in range(6):
            post = period >= 4
            outcome = (
                100
                + unit_index % (units // 2)
                + period
                + ((unit_index % 3) - 1) * period * 0.1
                + (pretrend * period if treated else 0)
            )
            if treated and post:
                outcome += 5
            observations.append(
                PanelObservation(
                    unit=unit,
                    observed_at=start + timedelta(days=period),
                    outcome=outcome,
                    treated=treated,
                    post_period=post,
                )
            )
    return GeoHoldoutInput(
        observations=tuple(observations),
        coordinates=coordinates,
        outcome_kind="revenue",
        spillover_pairs=(("geo-5", "geo-6"),),
    )


def test_valid_geo_design_reports_balance_map_and_business_impact() -> None:
    result = StatsmodelsGeoHoldoutEstimator().estimate(geo_panel(), random_seed=1_729)

    assert result.effect == pytest.approx(5.0)
    assert result.incremental_revenue == pytest.approx(60.0)
    assert result.diagnostics["design_assessment"] == "valid"
    assert result.diagnostics["balance_diagnostics"]  # type: ignore[index]
    assert len(result.diagnostics["geographic_assignments"]) == 12  # type: ignore[arg-type]
    assert result.diagnostics["spillover_warnings"]  # type: ignore[index]


def test_small_geo_design_is_weak() -> None:
    result = StatsmodelsGeoHoldoutEstimator().estimate(geo_panel(units=6), random_seed=1_729)

    assert result.diagnostics["design_assessment"] == "weak"
    assert result.diagnostics["causal_claim_allowed"] is False


def test_noncomparable_pretrends_make_geo_design_invalid() -> None:
    result = StatsmodelsGeoHoldoutEstimator().estimate(geo_panel(pretrend=5.0), random_seed=1_729)

    assert result.diagnostics["design_assessment"] == "invalid"
    assert result.diagnostics["causal_claim_allowed"] is False
