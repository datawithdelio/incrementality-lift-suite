from typing import Protocol
from uuid import UUID

from incrementality_api.application.datasets.validate_dataset import (
    ValidateDatasetCommand,
)
from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)


class ClaimNextValidationJobAction(Protocol):
    async def execute(
        self,
    ) -> DatasetValidationJob | None:
        """Claim the next available validation job."""


class ValidateDatasetAction(Protocol):
    async def execute(
        self,
        command: ValidateDatasetCommand,
    ) -> object:
        """Run the complete dataset-validation lifecycle."""


class MarkValidationJobSucceededAction(Protocol):
    async def execute(
        self,
        job_id: UUID,
    ) -> DatasetValidationJob:
        """Mark a claimed validation job successful."""


class RecordValidationJobFailureAction(Protocol):
    async def execute(
        self,
        *,
        job_id: UUID,
        error: str,
    ) -> DatasetValidationJob:
        """Retry or dead-letter a failed validation job."""


class RunNextDatasetValidationJob:
    """Process at most one durable dataset-validation job."""

    def __init__(
        self,
        *,
        claim_next: ClaimNextValidationJobAction,
        validate_dataset: ValidateDatasetAction,
        mark_succeeded: MarkValidationJobSucceededAction,
        record_failure: RecordValidationJobFailureAction,
    ) -> None:
        self._claim_next = claim_next
        self._validate_dataset = validate_dataset
        self._mark_succeeded = mark_succeeded
        self._record_failure = record_failure

    async def execute(
        self,
    ) -> DatasetValidationJob | None:
        job = await self._claim_next.execute()

        if job is None:
            return None

        command = ValidateDatasetCommand(
            workspace_id=job.workspace_id,
            project_id=job.project_id,
            dataset_id=job.dataset_id,
        )

        try:
            await self._validate_dataset.execute(
                command,
            )
        except Exception as error:
            error_message = str(error).strip()

            if not error_message:
                error_message = type(error).__name__

            return await self._record_failure.execute(
                job_id=job.id,
                error=error_message,
            )

        return await self._mark_succeeded.execute(
            job.id,
        )
