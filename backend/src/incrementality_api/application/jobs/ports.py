from datetime import datetime
from typing import Protocol
from uuid import UUID

from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)


class DatasetValidationJobRepository(Protocol):
    async def add(
        self,
        job: DatasetValidationJob,
    ) -> None:
        """Stage a new durable validation job."""

    async def get_by_id(
        self,
        job_id: UUID,
    ) -> DatasetValidationJob | None:
        """Load one durable job by ID."""

    async def get_by_dataset_id(
        self,
        dataset_id: UUID,
    ) -> DatasetValidationJob | None:
        """Load the validation job associated with a dataset."""

    async def get_next_available_for_update(
        self,
        *,
        available_at: datetime,
    ) -> DatasetValidationJob | None:
        """Lock and return the next claimable job."""

    async def update(
        self,
        job: DatasetValidationJob,
    ) -> None:
        """Stage updated durable-job lifecycle metadata."""
