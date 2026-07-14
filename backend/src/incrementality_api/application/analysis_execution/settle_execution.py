from uuid import UUID

from incrementality_api.application.analysis_execution.errors import (
    AnalysisExecutionJobUnavailableError,
    AnalysisExecutionRunUnavailableError,
)
from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
)
from incrementality_api.application.analysis_execution.ports import (
    AnalysisExecutionClock,
    AnalysisExecutionUnitOfWork,
)
from incrementality_api.application.analysis_execution.retry_policy import (
    AnalysisExecutionRetryPolicy,
)
from incrementality_api.domain.analysis_results.entities import AnalysisResult
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)


async def _load_locked_run(
    *,
    unit_of_work: AnalysisExecutionUnitOfWork,
    job: AnalysisExecutionJob,
) -> AnalysisRun:
    run = await unit_of_work.analysis_runs.get_by_scope_for_update(
        workspace_id=job.workspace_id,
        project_id=job.project_id,
        analysis_run_id=job.analysis_run_id,
    )
    if run is None:
        raise AnalysisExecutionRunUnavailableError("Analysis run is unavailable.")
    return run


class MarkAnalysisExecutionSucceeded:
    """Settle a successful job and its customer-visible run atomically."""

    def __init__(
        self,
        *,
        unit_of_work: AnalysisExecutionUnitOfWork,
        clock: AnalysisExecutionClock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(self, job_id: UUID) -> AnalysisExecutionJob:
        completed_at = self._clock.now()
        async with self._unit_of_work:
            job = await self._unit_of_work.execution_jobs.get_by_id_for_update(job_id)
            if job is None:
                raise AnalysisExecutionJobUnavailableError("Execution job is unavailable.")

            run = await _load_locked_run(unit_of_work=self._unit_of_work, job=job)
            succeeded_job = job.mark_succeeded(completed_at=completed_at)
            succeeded_run = run.mark_succeeded(completed_at=completed_at)

            await self._unit_of_work.execution_jobs.update(succeeded_job)
            await self._unit_of_work.analysis_runs.update(succeeded_run)
            await self._unit_of_work.commit()
            return succeeded_job


class PersistAnalysisExecutionSuccess:
    """Persist the canonical result and settle job/run success atomically."""

    def __init__(
        self,
        *,
        unit_of_work: AnalysisExecutionUnitOfWork,
        clock: AnalysisExecutionClock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(
        self,
        *,
        job_id: UUID,
        result: AnalysisEstimationResult,
    ) -> AnalysisExecutionJob:
        completed_at = self._clock.now()
        async with self._unit_of_work:
            job = await self._unit_of_work.execution_jobs.get_by_id_for_update(job_id)
            if job is None:
                raise AnalysisExecutionJobUnavailableError("Execution job is unavailable.")
            run = await _load_locked_run(unit_of_work=self._unit_of_work, job=job)
            persisted_result = AnalysisResult.create(
                workspace_id=run.workspace_id,
                project_id=run.project_id,
                analysis_run_id=run.id,
                dataset_id=run.dataset_id,
                semantic_mapping_id=run.semantic_mapping_id,
                semantic_mapping_version=run.semantic_mapping_version,
                estimator_type=run.estimator_type,
                estimator_version=run.estimator_version,
                library_name=result.library_name,
                library_version=result.library_version,
                effect=result.effect,
                standard_error=result.standard_error,
                p_value=result.p_value,
                confidence_interval_low=result.confidence_interval_low,
                confidence_interval_high=result.confidence_interval_high,
                sample_size=result.observation_count,
                diagnostics=result.diagnostics,
                incremental_outcome=result.incremental_outcome,
                relative_lift=result.relative_lift,
                incremental_revenue=result.incremental_revenue,
                incremental_conversions=result.incremental_conversions,
                created_at=completed_at,
            )
            succeeded_job = job.mark_succeeded(completed_at=completed_at)
            succeeded_run = run.mark_succeeded(completed_at=completed_at)
            await self._unit_of_work.analysis_results.add(persisted_result)
            await self._unit_of_work.execution_jobs.update(succeeded_job)
            await self._unit_of_work.analysis_runs.update(succeeded_run)
            await self._unit_of_work.commit()
            return succeeded_job


class RecordAnalysisExecutionFailure:
    """Retry or finally fail an execution job and its run atomically."""

    def __init__(
        self,
        *,
        unit_of_work: AnalysisExecutionUnitOfWork,
        clock: AnalysisExecutionClock,
        retry_policy: AnalysisExecutionRetryPolicy,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._retry_policy = retry_policy

    async def execute(
        self,
        *,
        job_id: UUID,
        error: str,
    ) -> AnalysisExecutionJob:
        failed_at = self._clock.now()
        async with self._unit_of_work:
            job = await self._unit_of_work.execution_jobs.get_by_id_for_update(job_id)
            if job is None:
                raise AnalysisExecutionJobUnavailableError("Execution job is unavailable.")

            run = await _load_locked_run(unit_of_work=self._unit_of_work, job=job)
            next_attempt_at = self._retry_policy.next_attempt_at(
                job=job,
                failed_at=failed_at,
            )

            if next_attempt_at is None:
                settled_job = job.mark_dead_letter(
                    completed_at=failed_at,
                    error=error,
                )
                settled_run = run.mark_failed(
                    completed_at=failed_at,
                    reason=error,
                )
            else:
                settled_job = job.retry(
                    failed_at=failed_at,
                    available_at=next_attempt_at,
                    error=error,
                )
                settled_run = run

            await self._unit_of_work.execution_jobs.update(settled_job)
            await self._unit_of_work.analysis_runs.update(settled_run)
            await self._unit_of_work.commit()
            return settled_job


class MarkAnalysisExecutionFailed:
    """Dead-letter a permanent execution failure and fail its run atomically."""

    def __init__(
        self,
        *,
        unit_of_work: AnalysisExecutionUnitOfWork,
        clock: AnalysisExecutionClock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(
        self,
        *,
        job_id: UUID,
        error: str,
    ) -> AnalysisExecutionJob:
        failed_at = self._clock.now()
        async with self._unit_of_work:
            job = await self._unit_of_work.execution_jobs.get_by_id_for_update(job_id)
            if job is None:
                raise AnalysisExecutionJobUnavailableError("Execution job is unavailable.")

            run = await _load_locked_run(unit_of_work=self._unit_of_work, job=job)
            failed_job = job.mark_dead_letter(completed_at=failed_at, error=error)
            failed_run = run.mark_failed(completed_at=failed_at, reason=error)

            await self._unit_of_work.execution_jobs.update(failed_job)
            await self._unit_of_work.analysis_runs.update(failed_run)
            await self._unit_of_work.commit()
            return failed_job
