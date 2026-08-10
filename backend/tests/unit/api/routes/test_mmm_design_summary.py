from uuid import uuid4

import pytest

from incrementality_api.api.v1.routes.data_products import (
    summarize_marketing_mix_design,
)
from incrementality_api.api.v1.schemas.data_products import (
    MarketingMixDesignSummaryRequest,
)
from incrementality_api.application.data_products.mmm_design_summary import (
    MarketingMixDesignSummary,
)
from incrementality_api.application.data_products.services import (
    DatasetProductQuery,
)


class FakeService:
    def __init__(self) -> None:
        self.scope: DatasetProductQuery | None = None
        self.configuration: dict[str, object] | None = None

    async def marketing_mix_design_summary(
        self,
        scope: DatasetProductQuery,
        *,
        configuration: dict[str, object],
    ) -> MarketingMixDesignSummary:
        self.scope = scope
        self.configuration = configuration
        return MarketingMixDesignSummary(
            period_count=3,
            saturation_half_spend_defaults={
                "search_spend": 20.0,
                "social_spend": 12.5,
            },
        )


@pytest.mark.asyncio
async def test_mmm_design_summary_route_preserves_mapping_and_configuration_contract() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()

    configuration = {
        "analysis_start_date": "2026-01-05",
        "analysis_end_date": "2026-01-19",
        "selected_geographies": ["north"],
        "excluded_geographies": [],
        "row_filters": [],
        "media_channels": [
            "search_spend",
            "social_spend",
        ],
    }

    request = MarketingMixDesignSummaryRequest(
        semantic_mapping_version=7,
        configuration=configuration,
    )
    service = FakeService()

    response = await summarize_marketing_mix_design(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        request=request,
        principal=object(),  # type: ignore[arg-type]
        service=service,  # type: ignore[arg-type]
    )

    assert service.scope == DatasetProductQuery(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        mapping_version=7,
    )
    assert service.configuration == configuration

    assert response.model_dump() == {
        "contract_version": "mmm-design-summary-v1",
        "period_count": 3,
        "saturation_half_spend_defaults": {
            "search_spend": 20.0,
            "social_spend": 12.5,
        },
    }
