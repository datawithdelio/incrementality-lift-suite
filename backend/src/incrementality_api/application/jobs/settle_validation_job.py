from datetime import timedelta
from uuid import UUID

from incrementality_api.application.jobs.errors import (
    ValidationJobUnavailableError,
)
from incrementality_api.application.jobs.ports import (
    DatasetValidationJobUnitOfWork,
    JobClock,
)
from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)


class MarkDatasetValidationJobSucceeded:
    """Persist successful completion of one claimed job."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetValidationJobUnitOfWork,
        clock: JobClock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(
        self,
        job_id: UUID,
    ) -> DatasetValidationJob:
        completed_at = self._clock.now()

        async with self._unit_of_work:
            job = await self._unit_of_work.validation_jobs.get_by_id_for_update(job_id)

            if job is None:
                raise ValidationJobUnavailableError("Validation job is unavailable.")

            succeeded_job = job.mark_succeeded(
                completed_at=completed_at,
            )

            await self._unit_of_work.validation_jobs.update(
                succeeded_job,
            )
            await self._unit_of_work.commit()

            return succeeded_job


class RecordDatasetValidationJobFailure:
    """Retry or dead-letter one failed claimed job."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetValidationJobUnitOfWork,
        clock: JobClock,
        retry_delay_seconds: int = 30,
    ) -> None:
        if retry_delay_seconds <= 0:
            raise ValueError("Retry delay must be positive.")

        self._unit_of_work = unit_of_work
        self._clock = clock
        self._retry_delay = timedelta(
            seconds=retry_delay_seconds,
        )

    async def execute(
        self,
        *,
        job_id: UUID,
        error: str,
    ) -> DatasetValidationJob:
        failed_at = self._clock.now()

        async with self._unit_of_work:
            job = await self._unit_of_work.validation_jobs.get_by_id_for_update(job_id)

            if job is None:
                raise ValidationJobUnavailableError("Validation job is unavailable.")

            if job.attempt_count >= job.max_attempts:
                settled_job = job.mark_dead_letter(
                    completed_at=failed_at,
                    error=error,
                )
            else:
                settled_job = job.retry(
                    failed_at=failed_at,
                    available_at=(failed_at + self._retry_delay),
                    error=error,
                )

            await self._unit_of_work.validation_jobs.update(
                settled_job,
            )
            await self._unit_of_work.commit()

            return settled_job
