import json
from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, cast
from uuid import UUID

from incrementality_api.domain.analysis_results.entities import AnalysisResult
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)
from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.domain.analysis_runs.status import AnalysisRunStatus


class AnalysisResultUnavailableError(Exception):
    """The requested run does not exist in the caller's complete scope."""


class AnalysisResultReadRepository(Protocol):
    async def get_by_analysis_run_scope(
        self, *, workspace_id: UUID, project_id: UUID, analysis_run_id: UUID
    ) -> AnalysisResult | None: ...


class AnalysisResultRunRepository(Protocol):
    async def get_by_scope(
        self, *, workspace_id: UUID, project_id: UUID, analysis_run_id: UUID
    ) -> AnalysisRun | None: ...


class AnalysisResultJobRepository(Protocol):
    async def get_by_analysis_run_scope(
        self, *, workspace_id: UUID, project_id: UUID, analysis_run_id: UUID
    ) -> AnalysisExecutionJob | None: ...


class AnalysisResultReadUnitOfWork(Protocol):
    @property
    def analysis_runs(self) -> AnalysisResultRunRepository: ...

    @property
    def execution_jobs(self) -> AnalysisResultJobRepository: ...

    @property
    def analysis_results(self) -> AnalysisResultReadRepository: ...

    async def __aenter__(self) -> "AnalysisResultReadUnitOfWork": ...

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class GetAnalysisResultQuery:
    workspace_id: UUID
    project_id: UUID
    analysis_run_id: UUID


@dataclass(frozen=True, slots=True)
class AnalysisResultView:
    run: AnalysisRun
    result: AnalysisResult | None
    lifecycle_status: str
    configuration: dict[str, object]
    attempt_count: int
    max_attempts: int
    failure_information: str | None


class GetAnalysisResult:
    """Retrieve a run and canonical result within full tenant/project scope."""

    def __init__(self, *, unit_of_work: AnalysisResultReadUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, query: GetAnalysisResultQuery) -> AnalysisResultView:
        async with self._unit_of_work:
            scope = {
                "workspace_id": query.workspace_id,
                "project_id": query.project_id,
                "analysis_run_id": query.analysis_run_id,
            }
            run = await self._unit_of_work.analysis_runs.get_by_scope(**scope)
            if run is None:
                raise AnalysisResultUnavailableError("Analysis run is unavailable.")
            job = await self._unit_of_work.execution_jobs.get_by_analysis_run_scope(**scope)
            result = await self._unit_of_work.analysis_results.get_by_analysis_run_scope(**scope)
            configuration_value = json.loads(run.configuration_json)
            if not isinstance(configuration_value, dict):
                raise RuntimeError("Persisted analysis configuration must be an object.")
            configuration = cast(dict[str, object], configuration_value)
            lifecycle_status = self._lifecycle_status(run=run, job=job)
            return AnalysisResultView(
                run=run,
                result=result,
                lifecycle_status=lifecycle_status,
                configuration=configuration,
                attempt_count=0 if job is None else job.attempt_count,
                max_attempts=0 if job is None else job.max_attempts,
                failure_information=self._safe_failure(run=run, lifecycle=lifecycle_status),
            )

    @staticmethod
    def _lifecycle_status(*, run: AnalysisRun, job: AnalysisExecutionJob | None) -> str:
        if (
            run.status is AnalysisRunStatus.RUNNING
            and job is not None
            and job.status is AnalysisExecutionJobStatus.PENDING
            and job.attempt_count > 0
        ):
            return "retrying"
        return run.status.value

    @staticmethod
    def _safe_failure(*, run: AnalysisRun, lifecycle: str) -> str | None:
        if lifecycle == "retrying":
            return "A temporary issue interrupted analysis. It will retry automatically."
        if run.status is AnalysisRunStatus.FAILED:
            return "Analysis could not be completed. Review the design and try again."
        return None
