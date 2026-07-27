from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from incrementality_api.api.v1.routes.data_products import (
    router,
    summarize_dataset_geographies,
)
from incrementality_api.application.data_products.geography_summary import (
    GeographyMetrics,
    GeographySummaryItem,
    GeographySummaryResult,
)
from incrementality_api.application.data_products.services import (
    DatasetProductQuery,
)


class FakeSummaryService:
    def __init__(self) -> None:
        self.scope: DatasetProductQuery | None = None

    async def geography_summary(
        self,
        scope: DatasetProductQuery,
    ) -> GeographySummaryResult:
        self.scope = scope

        return GeographySummaryResult(
            mapping_version=7,
            unit_column="geography",
            total_geographies=1,
            geographies=(
                GeographySummaryItem(
                    value="Newark",
                    observation_count=2184,
                    latitude=40.7357,
                    longitude=-74.1724,
                    coordinate_status="verified",
                    metrics=GeographyMetrics(
                        outcome_sum=8421,
                        spend_sum=43000,
                        covariate_sums={
                            "revenue": 250000,
                            "sessions": 123456,
                        },
                    ),
                ),
            ),
        )


async def test_geography_summary_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(
        router,
        prefix="/api/v1",
    )

    async with AsyncClient(
        transport=ASGITransport(
            app=app,
        ),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/workspaces/"
            f"{uuid4()}"
            "/projects/"
            f"{uuid4()}"
            "/datasets/"
            f"{uuid4()}"
            "/geography-summary"
        )

    assert response.status_code == 401


async def test_route_returns_real_summary_contract() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()

    service = FakeSummaryService()

    response = await summarize_dataset_geographies(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        principal=object(),
        service=service,  # type: ignore[arg-type]
        mapping_version=7,
    )

    assert service.scope == DatasetProductQuery(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        mapping_version=7,
    )

    assert response.mapping_version == 7
    assert response.unit_column == "geography"
    assert response.total_geographies == 1

    geography = response.geographies[0]

    assert geography.value == "Newark"
    assert geography.observation_count == 2184
    assert geography.latitude == 40.7357
    assert geography.longitude == -74.1724
    assert geography.coordinate_status == "verified"

    assert geography.metrics.outcome_sum == 8421
    assert geography.metrics.spend_sum == 43000
    assert geography.metrics.covariate_sums == {
        "revenue": 250000,
        "sessions": 123456,
    }
