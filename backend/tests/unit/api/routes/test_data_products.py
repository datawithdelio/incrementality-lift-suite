from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from incrementality_api.api.v1.routes.data_products import router


async def test_dataset_preview_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/workspaces/{uuid4()}/projects/{uuid4()}/datasets/{uuid4()}/preview"
        )
    assert response.status_code == 401
