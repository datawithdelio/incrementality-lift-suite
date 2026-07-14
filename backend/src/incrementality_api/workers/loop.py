import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)

SleepAction = Callable[[float], Awaitable[None]]

logger = logging.getLogger(__name__)


class ProcessNextValidationJobAction(Protocol):
    async def execute(
        self,
    ) -> DatasetValidationJob | None:
        """Process at most one validation job."""


class DatasetValidationWorker:
    """Continuously poll and process durable validation jobs."""

    def __init__(
        self,
        *,
        process_next: ProcessNextValidationJobAction,
        sleep: SleepAction,
        poll_interval_seconds: float = 1.0,
        error_retry_seconds: float = 5.0,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("Poll interval must be positive.")

        if error_retry_seconds <= 0:
            raise ValueError("Error retry delay must be positive.")

        self._process_next = process_next
        self._sleep = sleep
        self._poll_interval_seconds = poll_interval_seconds
        self._error_retry_seconds = error_retry_seconds

    async def run_once(
        self,
    ) -> DatasetValidationJob | None:
        try:
            job = await self._process_next.execute()
        except Exception:
            logger.exception("Unexpected validation worker failure.")

            await self._sleep(
                self._error_retry_seconds,
            )

            return None

        if job is None:
            await self._sleep(
                self._poll_interval_seconds,
            )

        return job

    async def run_forever(self) -> None:
        while True:
            await self.run_once()
