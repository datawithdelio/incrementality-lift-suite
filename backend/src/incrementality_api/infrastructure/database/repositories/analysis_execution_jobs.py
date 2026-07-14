from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)
from incrementality_api.infrastructure.database.models.analysis_execution_jobs import (
    AnalysisExecutionJobModel,
)


def to_analysis_execution_job_model(
    job: AnalysisExecutionJob,
) -> AnalysisExecutionJobModel:
    """Convert an execution-job entity into persisted state."""

    return AnalysisExecutionJobModel(
        id=job.id,
        workspace_id=job.workspace_id,
        project_id=job.project_id,
        analysis_run_id=job.analysis_run_id,
        status=job.status.value,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        available_at=job.available_at,
        claimed_at=job.claimed_at,
        completed_at=job.completed_at,
        last_error=job.last_error,
        created_at=job.created_at,
    )


def to_analysis_execution_job_entity(
    model: AnalysisExecutionJobModel,
) -> AnalysisExecutionJob:
    """Reconstruct an execution-job entity from persisted state."""

    return AnalysisExecutionJob(
        id=model.id,
        workspace_id=model.workspace_id,
        project_id=model.project_id,
        analysis_run_id=model.analysis_run_id,
        status=AnalysisExecutionJobStatus(model.status),
        attempt_count=model.attempt_count,
        max_attempts=model.max_attempts,
        available_at=model.available_at,
        claimed_at=model.claimed_at,
        completed_at=model.completed_at,
        last_error=model.last_error,
        created_at=model.created_at,
    )


class SqlAlchemyAnalysisExecutionJobRepository:
    """Persist and claim durable analysis execution jobs."""

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def add(
        self,
        job: AnalysisExecutionJob,
    ) -> None:
        self._session.add(to_analysis_execution_job_model(job))

        await self._session.flush()

    async def get_by_id(
        self,
        job_id: UUID,
    ) -> AnalysisExecutionJob | None:
        model = await self._session.scalar(
            select(AnalysisExecutionJobModel).where(
                AnalysisExecutionJobModel.id == job_id,
            )
        )

        if model is None:
            return None

        return to_analysis_execution_job_entity(model)

    async def get_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> AnalysisExecutionJob | None:
        model = await self._session.scalar(
            select(AnalysisExecutionJobModel).where(
                AnalysisExecutionJobModel.analysis_run_id == analysis_run_id,
            )
        )

        if model is None:
            return None

        return to_analysis_execution_job_entity(model)

    async def get_by_analysis_run_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisExecutionJob | None:
        model = await self._session.scalar(
            select(AnalysisExecutionJobModel).where(
                AnalysisExecutionJobModel.workspace_id == workspace_id,
                AnalysisExecutionJobModel.project_id == project_id,
                AnalysisExecutionJobModel.analysis_run_id == analysis_run_id,
            )
        )
        return None if model is None else to_analysis_execution_job_entity(model)

    async def get_next_available_for_update(
        self,
        *,
        available_at: datetime,
    ) -> AnalysisExecutionJob | None:
        statement = (
            select(AnalysisExecutionJobModel)
            .where(
                AnalysisExecutionJobModel.status == AnalysisExecutionJobStatus.PENDING.value,
                AnalysisExecutionJobModel.available_at <= available_at,
                AnalysisExecutionJobModel.attempt_count < AnalysisExecutionJobModel.max_attempts,
            )
            .order_by(
                AnalysisExecutionJobModel.available_at,
                AnalysisExecutionJobModel.created_at,
            )
            .limit(1)
            .with_for_update(
                skip_locked=True,
            )
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_analysis_execution_job_entity(model)

    async def get_by_id_for_update(
        self,
        job_id: UUID,
    ) -> AnalysisExecutionJob | None:
        model = await self._session.scalar(
            select(AnalysisExecutionJobModel)
            .where(
                AnalysisExecutionJobModel.id == job_id,
            )
            .with_for_update()
        )

        if model is None:
            return None

        return to_analysis_execution_job_entity(model)

    async def get_stale_running_for_update(
        self,
        *,
        claimed_before: datetime,
    ) -> AnalysisExecutionJob | None:
        statement = (
            select(AnalysisExecutionJobModel)
            .where(
                AnalysisExecutionJobModel.status == AnalysisExecutionJobStatus.RUNNING.value,
                AnalysisExecutionJobModel.claimed_at <= claimed_before,
            )
            .order_by(
                AnalysisExecutionJobModel.claimed_at,
                AnalysisExecutionJobModel.created_at,
            )
            .limit(1)
            .with_for_update(
                skip_locked=True,
            )
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_analysis_execution_job_entity(model)

    async def update(
        self,
        job: AnalysisExecutionJob,
    ) -> None:
        statement = (
            update(AnalysisExecutionJobModel)
            .where(
                AnalysisExecutionJobModel.id == job.id,
            )
            .values(
                workspace_id=job.workspace_id,
                project_id=job.project_id,
                analysis_run_id=(job.analysis_run_id),
                status=job.status.value,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
                available_at=job.available_at,
                claimed_at=job.claimed_at,
                completed_at=job.completed_at,
                last_error=job.last_error,
                updated_at=func.now(),
            )
        )

        await self._session.execute(statement)
        await self._session.flush()
