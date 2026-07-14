from incrementality_api.application.analysis_execution.errors import (
    AnalysisExecutionRunUnavailableError,
)
from incrementality_api.application.analysis_execution.ports import (
    AnalysisExecutionClock,
    AnalysisExecutionUnitOfWork,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)


class ClaimNextAnalysisExecutionJob:
    """Claim one available analysis execution job and start its run."""

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
    ) -> AnalysisExecutionJob | None:
        claimed_at = self._clock.now()

        async with self._unit_of_work:
            pending_job = await self._unit_of_work.execution_jobs.get_next_available_for_update(
                available_at=claimed_at,
            )

            if pending_job is None:
                return None

            run = await self._unit_of_work.analysis_runs.get_by_scope_for_update(
                workspace_id=pending_job.workspace_id,
                project_id=pending_job.project_id,
                analysis_run_id=(pending_job.analysis_run_id),
            )

            if run is None:
                raise AnalysisExecutionRunUnavailableError("Analysis run is unavailable.")

            running_job = pending_job.claim(
                claimed_at=claimed_at,
            )
            running_run = run.start(
                started_at=claimed_at,
            )

            await self._unit_of_work.execution_jobs.update(
                running_job,
            )
            await self._unit_of_work.analysis_runs.update(
                running_run,
            )

            await self._unit_of_work.commit()

            return running_job
