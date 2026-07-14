from datetime import timedelta

from incrementality_api.application.jobs.ports import (
    DatasetValidationJobUnitOfWork,
    JobClock,
)
from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)

RECOVERY_ERROR = "Worker claim expired before completion."


class RecoverStaleDatasetValidationJob:
    """Recover one validation job abandoned by a worker."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetValidationJobUnitOfWork,
        clock: JobClock,
        claim_timeout_seconds: int = 300,
    ) -> None:
        if claim_timeout_seconds <= 0:
            raise ValueError("Claim timeout must be positive.")

        self._unit_of_work = unit_of_work
        self._clock = clock
        self._claim_timeout = timedelta(
            seconds=claim_timeout_seconds,
        )

    async def execute(
        self,
    ) -> DatasetValidationJob | None:
        current_time = self._clock.now()
        claimed_before = current_time - self._claim_timeout

        async with self._unit_of_work:
            job = await self._unit_of_work.validation_jobs.get_stale_running_for_update(
                claimed_before=claimed_before,
            )

            if job is None:
                return None

            if job.attempt_count >= job.max_attempts:
                recovered_job = job.mark_dead_letter(
                    completed_at=current_time,
                    error=RECOVERY_ERROR,
                )
            else:
                recovered_job = job.retry(
                    failed_at=current_time,
                    available_at=current_time,
                    error=RECOVERY_ERROR,
                )

            await self._unit_of_work.validation_jobs.update(
                recovered_job,
            )
            await self._unit_of_work.commit()

            return recovered_job
