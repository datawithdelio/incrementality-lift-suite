import logging
from typing import Protocol

from incrementality_api.domain.health.models import (
    HealthCheckResult,
    HealthState,
)

logger = logging.getLogger(__name__)


class DatabaseProbe(Protocol):
    async def ping(self) -> None:
        """Raise an exception when the database cannot be reached."""


class CheckReadiness:
    """Determine whether infrastructure is ready to serve traffic."""

    def __init__(self, database_probe: DatabaseProbe) -> None:
        self._database_probe = database_probe

    async def execute(self) -> HealthCheckResult:
        try:
            await self._database_probe.ping()
        except Exception:
            logger.exception("Database readiness check failed")

            return HealthCheckResult(
                status=HealthState.NOT_READY,
                checks={"database": "unavailable"},
            )

        return HealthCheckResult(
            status=HealthState.OK,
            checks={"database": "ok"},
        )
