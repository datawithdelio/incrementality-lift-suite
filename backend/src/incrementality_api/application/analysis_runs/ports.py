from datetime import datetime
from types import TracebackType
from typing import Protocol
from uuid import UUID

from incrementality_api.application.datasets.ports import (
    DatasetRepository,
    DatasetSemanticMappingRepository,
)
from incrementality_api.domain.analysis_results.entities import AnalysisResult
from incrementality_api.domain.analysis_runs.entities import (
    AnalysisRun,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)


class AnalysisRunRepository(Protocol):
    async def add(
        self,
        run: AnalysisRun,
    ) -> None:
        """Stage one analysis run for persistence."""

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisRun | None:
        """Load one run within complete tenant scope."""

    async def update(
        self,
        run: AnalysisRun,
    ) -> None:
        """Stage updated analysis-run lifecycle metadata."""


class AnalysisExecutionJobRepository(Protocol):
    async def add(
        self,
        job: AnalysisExecutionJob,
    ) -> None: ...

    async def get_by_analysis_run_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisExecutionJob | None: ...


class AnalysisResultRepository(Protocol):
    async def get_by_analysis_run_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisResult | None: ...


class AnalysisRunUnitOfWork(Protocol):
    @property
    def datasets(self) -> DatasetRepository: ...

    @property
    def semantic_mappings(self) -> DatasetSemanticMappingRepository: ...

    @property
    def analysis_runs(self) -> AnalysisRunRepository: ...

    @property
    def execution_jobs(self) -> AnalysisExecutionJobRepository: ...

    @property
    def analysis_results(self) -> AnalysisResultRepository: ...

    async def __aenter__(
        self,
    ) -> "AnalysisRunUnitOfWork":
        """Open one analysis-run transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back failures and close the transaction."""

    async def commit(self) -> None:
        """Commit analysis-run metadata atomically."""


class AnalysisRunClock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware timestamp."""
