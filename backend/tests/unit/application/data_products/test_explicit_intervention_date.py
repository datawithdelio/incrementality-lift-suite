from incrementality_api.application.data_products.explorer import (
    DatasetExplorer,
    DatasetExplorerQuery,
    ExplorerSemanticMapping,
)


def test_explicit_intervention_date_drives_real_pre_post_periods() -> None:
    rows = (
        {
            "date": "2025-06-30",
            "geography": "Newark",
            "treatment": "1",
            "conversions": "100",
        },
        {
            "date": "2025-06-30",
            "geography": "Elizabeth",
            "treatment": "0",
            "conversions": "90",
        },
        {
            "date": "2025-07-01",
            "geography": "Newark",
            "treatment": "1",
            "conversions": "120",
        },
        {
            "date": "2025-07-01",
            "geography": "Elizabeth",
            "treatment": "0",
            "conversions": "92",
        },
    )

    mapping = ExplorerSemanticMapping(
        time_column="date",
        unit_column="geography",
        treatment_column="treatment",
        outcome_column="conversions",
        treatment_value="1",
        control_value="0",
    )

    result = DatasetExplorer().execute(
        rows,
        DatasetExplorerQuery(
            intervention_date="2025-07-01",
        ),
        mapping,
    )

    assert result.visualizations.treatment_start_date == "2025-07-01"
    assert [point.phase for point in result.visualizations.trend] == [
        "pre",
        "post",
    ]

    balance = result.visualizations.balance
    assert balance is not None
    assert balance.treatment_pre_count == 1
    assert balance.treatment_post_count == 1
    assert balance.control_pre_count == 1
    assert balance.control_post_count == 1


def test_intervention_date_must_be_inside_dataset_range() -> None:
    rows = (
        {
            "date": "2025-06-30",
            "geography": "Newark",
            "treatment": "1",
            "conversions": "100",
        },
        {
            "date": "2025-07-01",
            "geography": "Elizabeth",
            "treatment": "0",
            "conversions": "90",
        },
    )

    mapping = ExplorerSemanticMapping(
        time_column="date",
        unit_column="geography",
        treatment_column="treatment",
        outcome_column="conversions",
        treatment_value="1",
        control_value="0",
    )

    try:
        DatasetExplorer().execute(
            rows,
            DatasetExplorerQuery(
                intervention_date="2026-01-01",
            ),
            mapping,
        )
    except ValueError as error:
        assert str(error) == (
            "Intervention date must fall inside the dataset date range."
        )
    else:
        raise AssertionError("Expected an invalid intervention date.")
