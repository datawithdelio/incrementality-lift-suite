from incrementality_api.application.jobs.ports import (
    DatasetValidationJobUnitOfWork,
    JobClock,
)
from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)


class ClaimNextDatasetValidationJob:
    """Claim the oldest currently available validation job."""

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
    ) -> DatasetValidationJob | None:
        claimed_at = self._clock.now()

        async with self._unit_of_work:
            pending_job = await self._unit_of_work.validation_jobs.get_next_available_for_update(
                available_at=claimed_at,
            )

            if pending_job is None:
                return None

            running_job = pending_job.claim(
                claimed_at=claimed_at,
            )

            await self._unit_of_work.validation_jobs.update(
                running_job,
            )
            await self._unit_of_work.commit()

            return running_job
