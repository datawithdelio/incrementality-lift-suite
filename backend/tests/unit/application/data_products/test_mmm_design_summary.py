from incrementality_api.application.data_products.mmm_design_summary import (
    MarketingMixDesignSummaryBuilder,
)


def test_half_spend_defaults_use_median_of_period_aggregated_channel_spend() -> None:
    rows = (
        {
            "date": "2026-01-05",
            "region": "north",
            "search_spend": "10",
            "social_spend": "4",
        },
        {
            "date": "2026-01-05",
            "region": "south",
            "search_spend": "20",
            "social_spend": "6",
        },
        {
            "date": "2026-01-12",
            "region": "north",
            "search_spend": "20",
            "social_spend": "8",
        },
        {
            "date": "2026-01-12",
            "region": "south",
            "search_spend": "30",
            "social_spend": "12",
        },
        {
            "date": "2026-01-19",
            "region": "north",
            "search_spend": "30",
            "social_spend": "12",
        },
        {
            "date": "2026-01-19",
            "region": "south",
            "search_spend": "40",
            "social_spend": "18",
        },
    )

    result = MarketingMixDesignSummaryBuilder().build(
        rows=rows,
        time_column="date",
        media_channels=("search_spend", "social_spend"),
    )

    assert result.period_count == 3

    # search period totals: 30, 50, 70 -> median 50
    assert result.saturation_half_spend_defaults["search_spend"] == 50.0

    # social period totals: 10, 20, 30 -> median 20
    assert result.saturation_half_spend_defaults["social_spend"] == 20.0


def test_design_summary_rejects_invalid_media_values() -> None:
    rows = (
        {
            "date": "2026-01-05",
            "search_spend": "not-a-number",
        },
    )

    try:
        MarketingMixDesignSummaryBuilder().build(
            rows=rows,
            time_column="date",
            media_channels=("search_spend",),
        )
    except ValueError as error:
        assert "invalid MMM design-summary values" in str(error)
    else:
        raise AssertionError("Expected invalid MMM values to be rejected.")

from incrementality_api.application.analysis_execution.input_loading import (
    AnalysisPeriodRowFilter,
)
from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.infrastructure.analysis_execution.selection import (
    AnalysisSelectionRowExecutor,
)

from incrementality_api.application.data_products.mmm_design_summary import (
    MarketingMixDesignSummaryPlanner,
)


def test_design_summary_matches_analysis_period_and_geography_selection() -> None:
    mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="region",
        treatment_column=None,
        outcome_column="conversions",
        spend_column="total_spend",
        covariate_columns=(),
        treatment_value=None,
        control_value=None,
    )

    period = AnalysisPeriodSnapshot.from_configuration(
        AnalysisEstimatorType.MARKETING_MIX_MODEL,
        {
            "analysis_start_date": "2026-01-05",
            "analysis_end_date": "2026-01-19",
        },
    )

    selection = AnalysisSelectionSnapshot.from_configuration(
        estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
        configuration={
            "selected_geographies": ["north"],
        },
        semantic_mapping=mapping,
    )

    rows = (
        # Outside the configured period. This extreme value must not affect
        # the design-summary default.
        {
            "date": "2025-12-29",
            "region": "north",
            "search_spend": "9999",
        },
        {
            "date": "2026-01-05",
            "region": "north",
            "search_spend": "10",
        },
        {
            "date": "2026-01-05",
            "region": "south",
            "search_spend": "20",
        },
        {
            "date": "2026-01-12",
            "region": "north",
            "search_spend": "20",
        },
        {
            "date": "2026-01-12",
            "region": "south",
            "search_spend": "30",
        },
        {
            "date": "2026-01-19",
            "region": "north",
            "search_spend": "30",
        },
        {
            "date": "2026-01-19",
            "region": "south",
            "search_spend": "40",
        },
        # Also outside the configured period.
        {
            "date": "2026-01-26",
            "region": "north",
            "search_spend": "8888",
        },
    )

    result = MarketingMixDesignSummaryPlanner(
        period_filter=AnalysisPeriodRowFilter(),
        selection_executor=AnalysisSelectionRowExecutor(),
        summary_builder=MarketingMixDesignSummaryBuilder(),
    ).build(
        rows=rows,
        mapping=mapping,
        period=period,
        selection=selection,
        media_channels=("search_spend",),
    )

    assert result.period_count == 3

    # In-window north-only spend = 10, 20, 30 -> median 20.
    #
    # This proves we are NOT using:
    # - the complete dataset,
    # - the south geography,
    # - or raw unfiltered column medians.
    assert result.saturation_half_spend_defaults["search_spend"] == 20.0


def test_design_summary_planner_accepts_canonical_mmm_run_configuration() -> None:
    mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="region",
        treatment_column=None,
        outcome_column="conversions",
        spend_column="total_spend",
        covariate_columns=(),
        treatment_value=None,
        control_value=None,
    )

    rows = (
        {
            "date": "2025-12-29",
            "region": "north",
            "search_spend": "9999",
        },
        {
            "date": "2026-01-05",
            "region": "north",
            "search_spend": "10",
        },
        {
            "date": "2026-01-05",
            "region": "south",
            "search_spend": "20",
        },
        {
            "date": "2026-01-12",
            "region": "north",
            "search_spend": "20",
        },
        {
            "date": "2026-01-12",
            "region": "south",
            "search_spend": "30",
        },
        {
            "date": "2026-01-19",
            "region": "north",
            "search_spend": "30",
        },
        {
            "date": "2026-01-19",
            "region": "south",
            "search_spend": "40",
        },
    )

    configuration = {
        "analysis_start_date": "2026-01-05",
        "analysis_end_date": "2026-01-19",
        "selected_geographies": ["north"],
        "excluded_geographies": [],
        "row_filters": [],
        "media_channels": ["search_spend"],
        "control_columns": [],
        "aggregate_spend_column": "total_spend",
        "outcome_kind": "conversions",
        "seasonality_period": 52,
        "adstock_decay": {"search_spend": 0.0},
        "saturation_half_spend": {"search_spend": 1.0},
    }

    result = MarketingMixDesignSummaryPlanner(
        period_filter=AnalysisPeriodRowFilter(),
        selection_executor=AnalysisSelectionRowExecutor(),
        summary_builder=MarketingMixDesignSummaryBuilder(),
    ).build_from_configuration(
        rows=rows,
        mapping=mapping,
        configuration=configuration,
    )

    assert result.period_count == 3
    assert result.saturation_half_spend_defaults == {
        "search_spend": 20.0,
    }


def test_design_summary_planner_rejects_invalid_canonical_media_channels() -> None:
    mapping = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="region",
        treatment_column=None,
        outcome_column="conversions",
        spend_column="total_spend",
        covariate_columns=(),
        treatment_value=None,
        control_value=None,
    )

    configuration = {
        "analysis_start_date": "2026-01-05",
        "analysis_end_date": "2026-01-19",
        "selected_geographies": [],
        "excluded_geographies": [],
        "row_filters": [],
        "media_channels": [],
    }

    try:
        MarketingMixDesignSummaryPlanner(
            period_filter=AnalysisPeriodRowFilter(),
            selection_executor=AnalysisSelectionRowExecutor(),
            summary_builder=MarketingMixDesignSummaryBuilder(),
        ).build_from_configuration(
            rows=(
                {
                    "date": "2026-01-05",
                    "region": "north",
                    "search_spend": "10",
                },
            ),
            mapping=mapping,
            configuration=configuration,
        )
    except ValueError as error:
        assert "media_channels" in str(error)
    else:
        raise AssertionError("Expected invalid MMM media_channels to be rejected.")

from types import SimpleNamespace
from uuid import uuid4

from incrementality_api.application.data_products.services import (
    DatasetProductQuery,
    ProductionDataProducts,
)


class StubMmmDesignSummaryDataProducts(ProductionDataProducts):
    def __init__(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        mapping: object,
        planner: MarketingMixDesignSummaryPlanner,
    ) -> None:
        super().__init__(
            unit_of_work=object(),
            object_storage=object(),
            quality_writer=object(),
        )  # type: ignore[arg-type]
        self._stub_rows = rows
        self._stub_mapping = mapping
        self._mmm_design_summary_planner = planner

    async def _load(self, scope: DatasetProductQuery):  # type: ignore[override]
        del scope
        return self._stub_rows, self._stub_mapping


async def test_data_products_builds_mmm_design_summary_from_dataset_mapping_and_configuration() -> None:
    rows = (
        {
            "date": "2025-12-29",
            "region": "north",
            "search_spend": "9999",
        },
        {
            "date": "2026-01-05",
            "region": "north",
            "search_spend": "10",
        },
        {
            "date": "2026-01-05",
            "region": "south",
            "search_spend": "20",
        },
        {
            "date": "2026-01-12",
            "region": "north",
            "search_spend": "20",
        },
        {
            "date": "2026-01-12",
            "region": "south",
            "search_spend": "30",
        },
        {
            "date": "2026-01-19",
            "region": "north",
            "search_spend": "30",
        },
        {
            "date": "2026-01-19",
            "region": "south",
            "search_spend": "40",
        },
    )

    mapping = SimpleNamespace(
        version=7,
        time_column="date",
        unit_column="region",
        treatment_column=None,
        outcome_column="conversions",
        spend_column="total_spend",
        covariate_columns=(),
        treatment_value=None,
        control_value=None,
    )

    configuration = {
        "analysis_start_date": "2026-01-05",
        "analysis_end_date": "2026-01-19",
        "selected_geographies": ["north"],
        "excluded_geographies": [],
        "row_filters": [],
        "media_channels": ["search_spend"],
        "control_columns": [],
        "aggregate_spend_column": "total_spend",
        "outcome_kind": "conversions",
        "seasonality_period": 52,
        "adstock_decay": {"search_spend": 0.0},
        "saturation_half_spend": {"search_spend": 1.0},
    }

    service = StubMmmDesignSummaryDataProducts(
        rows=rows,
        mapping=mapping,
        planner=MarketingMixDesignSummaryPlanner(
            period_filter=AnalysisPeriodRowFilter(),
            selection_executor=AnalysisSelectionRowExecutor(),
            summary_builder=MarketingMixDesignSummaryBuilder(),
        ),
    )

    result = await service.marketing_mix_design_summary(
        DatasetProductQuery(
            workspace_id=uuid4(),
            project_id=uuid4(),
            dataset_id=uuid4(),
            mapping_version=7,
        ),
        configuration=configuration,
    )

    assert result.period_count == 3
    assert result.saturation_half_spend_defaults == {
        "search_spend": 20.0,
    }
