from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)
from incrementality_api.domain.jobs.status import (
    DatasetValidationJobStatus,
)
from incrementality_api.infrastructure.database.models.jobs import (
    DatasetValidationJobModel,
)


def to_dataset_validation_job_model(
    job: DatasetValidationJob,
) -> DatasetValidationJobModel:
    """Convert the domain job into its persistence model."""

    return DatasetValidationJobModel(
        id=job.id,
        workspace_id=job.workspace_id,
        project_id=job.project_id,
        dataset_id=job.dataset_id,
        status=job.status.value,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        available_at=job.available_at,
        claimed_at=job.claimed_at,
        completed_at=job.completed_at,
        last_error=job.last_error,
        created_at=job.created_at,
        updated_at=job.created_at,
    )


def to_dataset_validation_job_entity(
    model: DatasetValidationJobModel,
) -> DatasetValidationJob:
    """Convert a persistence model into the domain job."""

    return DatasetValidationJob(
        id=model.id,
        workspace_id=model.workspace_id,
        project_id=model.project_id,
        dataset_id=model.dataset_id,
        status=DatasetValidationJobStatus(
            model.status,
        ),
        attempt_count=model.attempt_count,
        max_attempts=model.max_attempts,
        available_at=model.available_at,
        created_at=model.created_at,
        claimed_at=model.claimed_at,
        completed_at=model.completed_at,
        last_error=model.last_error,
    )


class SqlAlchemyDatasetValidationJobRepository:
    """Persist and claim durable dataset-validation jobs."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def add(
        self,
        job: DatasetValidationJob,
    ) -> None:
        self._session.add(
            to_dataset_validation_job_model(job),
        )
        await self._session.flush()

    async def get_by_id(
        self,
        job_id: UUID,
    ) -> DatasetValidationJob | None:
        statement = select(DatasetValidationJobModel).where(
            DatasetValidationJobModel.id == job_id,
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_dataset_validation_job_entity(model)

    async def get_by_id_for_update(
        self,
        job_id: UUID,
    ) -> DatasetValidationJob | None:
        statement = (
            select(DatasetValidationJobModel)
            .where(
                DatasetValidationJobModel.id == job_id,
            )
            .with_for_update()
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_dataset_validation_job_entity(model)

    async def get_by_dataset_id(
        self,
        dataset_id: UUID,
    ) -> DatasetValidationJob | None:
        statement = select(DatasetValidationJobModel).where(
            DatasetValidationJobModel.dataset_id == dataset_id,
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_dataset_validation_job_entity(model)

    async def get_next_available_for_update(
        self,
        *,
        available_at: datetime,
    ) -> DatasetValidationJob | None:
        statement = (
            select(DatasetValidationJobModel)
            .where(
                DatasetValidationJobModel.status == DatasetValidationJobStatus.PENDING.value,
                DatasetValidationJobModel.available_at <= available_at,
                DatasetValidationJobModel.attempt_count < DatasetValidationJobModel.max_attempts,
            )
            .order_by(
                DatasetValidationJobModel.available_at,
                DatasetValidationJobModel.created_at,
                DatasetValidationJobModel.id,
            )
            .limit(1)
            .with_for_update(
                skip_locked=True,
            )
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_dataset_validation_job_entity(model)

    async def get_stale_running_for_update(
        self,
        *,
        claimed_before: datetime,
    ) -> DatasetValidationJob | None:
        statement = (
            select(DatasetValidationJobModel)
            .where(
                DatasetValidationJobModel.status == DatasetValidationJobStatus.RUNNING.value,
                DatasetValidationJobModel.claimed_at <= claimed_before,
            )
            .order_by(
                DatasetValidationJobModel.claimed_at,
                DatasetValidationJobModel.created_at,
                DatasetValidationJobModel.id,
            )
            .limit(1)
            .with_for_update(
                skip_locked=True,
            )
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_dataset_validation_job_entity(model)

    async def update(
        self,
        job: DatasetValidationJob,
    ) -> None:
        statement = (
            sql_update(DatasetValidationJobModel)
            .where(
                DatasetValidationJobModel.id == job.id,
            )
            .values(
                status=job.status.value,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
                available_at=job.available_at,
                claimed_at=job.claimed_at,
                completed_at=job.completed_at,
                last_error=job.last_error,
            )
        )

        await self._session.execute(statement)
        await self._session.flush()
