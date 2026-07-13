from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from incrementality_api.api.dependencies.health import get_database_probe
from incrementality_api.api.v1.schemas.health import HealthResponse
from incrementality_api.application.health.check_liveness import (
    CheckLiveness,
)
from incrementality_api.application.health.check_readiness import (
    CheckReadiness,
    DatabaseProbe,
)
from incrementality_api.domain.health.models import HealthState

router = APIRouter(
    prefix="/health",
    tags=["health"],
)

DatabaseProbeDependency = Annotated[
    DatabaseProbe,
    Depends(get_database_probe),
]


@router.get(
    "/live",
    response_model=HealthResponse,
    summary="Check application liveness",
)
async def check_liveness() -> HealthResponse:
    result = CheckLiveness().execute()

    return HealthResponse(
        status=result.status,
        checks=dict(result.checks),
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Check application readiness",
)
async def check_readiness(
    response: Response,
    database_probe: DatabaseProbeDependency,
) -> HealthResponse:
    result = await CheckReadiness(
        database_probe=database_probe,
    ).execute()

    if result.status is HealthState.NOT_READY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=result.status,
        checks=dict(result.checks),
    )
