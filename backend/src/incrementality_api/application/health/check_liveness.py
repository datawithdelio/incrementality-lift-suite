from incrementality_api.domain.health.models import (
    HealthCheckResult,
    HealthState,
)


class CheckLiveness:
    """Confirm that the API process itself is running."""

    def execute(self) -> HealthCheckResult:
        return HealthCheckResult(
            status=HealthState.OK,
            checks={"application": "ok"},
        )
