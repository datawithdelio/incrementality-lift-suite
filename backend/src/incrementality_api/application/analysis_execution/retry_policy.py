from datetime import datetime, timedelta
from typing import Protocol

from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)


class AnalysisExecutionRetryPolicy(Protocol):
    def next_attempt_at(
        self,
        *,
        job: AnalysisExecutionJob,
        failed_at: datetime,
    ) -> datetime | None:
        """Return retry availability or None when the failure is final."""


class FixedDelayAnalysisExecutionRetryPolicy:
    """Retry unfinished jobs after a fixed delay until attempts are exhausted."""

    def __init__(self, *, retry_delay_seconds: int = 30) -> None:
        if retry_delay_seconds <= 0:
            raise ValueError("Retry delay must be positive.")
        self._retry_delay = timedelta(seconds=retry_delay_seconds)

    def next_attempt_at(
        self,
        *,
        job: AnalysisExecutionJob,
        failed_at: datetime,
    ) -> datetime | None:
        if job.attempt_count >= job.max_attempts:
            return None
        return failed_at + self._retry_delay
