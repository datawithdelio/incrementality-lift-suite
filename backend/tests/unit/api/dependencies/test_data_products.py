from incrementality_api.api.dependencies import data_products as dependencies
from incrementality_api.application.data_products.mmm_design_summary import (
    MarketingMixDesignSummaryPlanner,
)


def test_get_data_products_service_wires_mmm_design_summary_planner(
    monkeypatch,
) -> None:
    sessions = object()

    monkeypatch.setattr(
        dependencies,
        "get_session_factory",
        lambda: sessions,
    )
    monkeypatch.setattr(
        dependencies,
        "get_data_product_storage",
        lambda: object(),
    )
    monkeypatch.setattr(
        dependencies,
        "SqlAlchemyDatasetUnitOfWork",
        lambda received_sessions: object(),
    )
    monkeypatch.setattr(
        dependencies,
        "SqlAlchemyQualityAssessmentWriter",
        lambda received_sessions, clock: object(),
    )

    service = dependencies.get_data_products_service()

    assert isinstance(
        service._mmm_design_summary_planner,
        MarketingMixDesignSummaryPlanner,
    )
