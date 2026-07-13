import pytest

from incrementality_api.application.health.check_liveness import CheckLiveness
from incrementality_api.application.health.check_readiness import CheckReadiness
from incrementality_api.domain.health.models import HealthState


class HealthyDatabaseProbe:
    async def ping(self) -> None:
        return None


class UnhealthyDatabaseProbe:
    async def ping(self) -> None:
        raise ConnectionError("Database unavailable")


def test_liveness_does_not_depend_on_external_infrastructure() -> None:
    result = CheckLiveness().execute()

    assert result.status is HealthState.OK
    assert result.checks == {"application": "ok"}


@pytest.mark.asyncio
async def test_readiness_succeeds_when_database_is_available() -> None:
    service = CheckReadiness(database_probe=HealthyDatabaseProbe())

    result = await service.execute()

    assert result.status is HealthState.OK
    assert result.checks == {"database": "ok"}


@pytest.mark.asyncio
async def test_readiness_fails_when_database_is_unavailable() -> None:
    service = CheckReadiness(database_probe=UnhealthyDatabaseProbe())

    result = await service.execute()

    assert result.status is HealthState.NOT_READY
    assert result.checks == {"database": "unavailable"}
