from dataclasses import dataclass

from incrementality_api.application.data_products.geography_summary import (
    GeographySummaryBuilder,
)


@dataclass(frozen=True)
class Mapping:
    version: int = 3
    unit_column: str = "geography"
    outcome_column: str = "conversions"
    spend_column: str | None = "ad_spend"
    covariate_columns: tuple[str, ...] = (
        "sessions",
        "conversion_rate",
        "revenue",
    )


def test_builds_complete_real_geography_summary() -> None:
    rows = (
        {
            "geography": "Newark",
            "conversions": "20",
            "ad_spend": "100",
            "sessions": "1000",
            "conversion_rate": "0.02",
            "revenue": "500",
            "latitude": "40.7357",
            "longitude": "-74.1724",
        },
        {
            "geography": "Newark",
            "conversions": "30",
            "ad_spend": "150",
            "sessions": "1200",
            "conversion_rate": "0.025",
            "revenue": "750",
            "latitude": "40.7357",
            "longitude": "-74.1724",
        },
        {
            "geography": "Elizabeth",
            "conversions": "15",
            "ad_spend": "90",
            "sessions": "800",
            "conversion_rate": "0.01875",
            "revenue": "400",
            "latitude": "",
            "longitude": "",
        },
    )

    result = GeographySummaryBuilder().build(rows, Mapping())

    assert result.mapping_version == 3
    assert result.unit_column == "geography"
    assert result.total_geographies == 2

    elizabeth, newark = result.geographies

    assert elizabeth.value == "Elizabeth"
    assert elizabeth.coordinate_status == "missing"
    assert elizabeth.latitude is None
    assert elizabeth.longitude is None

    assert newark.value == "Newark"
    assert newark.observation_count == 2
    assert newark.coordinate_status == "verified"
    assert newark.latitude == 40.7357
    assert newark.longitude == -74.1724
    assert newark.metrics.outcome_sum == 50
    assert newark.metrics.spend_sum == 250
    assert newark.metrics.covariate_sums == {
        "conversion_rate": 0.045,
        "revenue": 1250,
        "sessions": 2200,
    }


def test_never_guesses_coordinates_and_rejects_conflicts() -> None:
    rows = (
        {
            "geography": "Newark",
            "conversions": "10",
            "ad_spend": "20",
            "latitude": "40.7357",
            "longitude": "-74.1724",
        },
        {
            "geography": "Newark",
            "conversions": "12",
            "ad_spend": "22",
            "latitude": "41.0000",
            "longitude": "-74.1724",
        },
        {
            "geography": "Paterson",
            "conversions": "8",
            "ad_spend": "14",
        },
    )

    result = GeographySummaryBuilder().build(rows, Mapping())

    by_name = {
        item.value: item
        for item in result.geographies
    }

    assert by_name["Newark"].coordinate_status == "missing"
    assert by_name["Newark"].latitude is None
    assert by_name["Newark"].longitude is None

    assert by_name["Paterson"].coordinate_status == "missing"
    assert by_name["Paterson"].latitude is None
    assert by_name["Paterson"].longitude is None


def test_uses_all_rows_without_preview_pagination() -> None:
    rows = tuple(
        {
            "geography": f"Geo-{index}",
            "conversions": str(index + 1),
            "ad_spend": str((index + 1) * 10),
        }
        for index in range(125)
    )

    result = GeographySummaryBuilder().build(rows, Mapping())

    assert result.total_geographies == 125
    assert len(result.geographies) == 125
