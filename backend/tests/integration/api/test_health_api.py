from httpx import ASGITransport, AsyncClient

from incrementality_api.main import create_app


async def test_liveness_endpoint_returns_success() -> None:
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "application": "ok",
        },
    }
