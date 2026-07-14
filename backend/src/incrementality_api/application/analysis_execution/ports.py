from datetime import datetime
from types import TracebackType
from typing import Protocol
from uuid import UUID

from incrementality_api.domain.analysis_runs.entities import (
    AnalysisRun,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)


class AnalysisExecutionJobRepository(Protocol):
    async def get_next_available_for_update(
        self,
        *,
        available_at: datetime,
    ) -> AnalysisExecutionJob | None:
        """Lock and return the oldest available execution job."""

    async def get_by_id_for_update(
        self,
        job_id: UUID,
    ) -> AnalysisExecutionJob | None:
        """Lock one execution job by ID."""

    async def get_stale_running_for_update(
        self,
        *,
        claimed_before: datetime,
    ) -> AnalysisExecutionJob | None:
        """Lock one abandoned running execution job."""

    async def update(
        self,
        job: AnalysisExecutionJob,
    ) -> None:
        """Stage updated execution-job lifecycle metadata."""


class AnalysisExecutionRunRepository(Protocol):
    async def get_by_scope_for_update(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisRun | None:
        """Lock one analysis run within complete tenant scope."""

    async def update(
        self,
        run: AnalysisRun,
    ) -> None:
        """Stage updated analysis-run lifecycle metadata."""


class AnalysisExecutionUnitOfWork(Protocol):
    execution_jobs: AnalysisExecutionJobRepository
    analysis_runs: AnalysisExecutionRunRepository

    async def __aenter__(
        self,
    ) -> "AnalysisExecutionUnitOfWork":
        """Open one analysis-execution transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back failures and close the transaction."""

    async def commit(self) -> None:
        """Commit execution-job and analysis-run metadata."""


class AnalysisExecutionClock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware timestamp."""
