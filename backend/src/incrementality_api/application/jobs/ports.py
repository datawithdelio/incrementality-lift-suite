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

    async def get_by_id_for_update(
        self,
        job_id: UUID,
    ) -> DatasetValidationJob | None:
        """Lock and load one durable job by ID."""

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

    async def get_stale_running_for_update(
        self,
        *,
        claimed_before: datetime,
    ) -> DatasetValidationJob | None:
        """Lock and return one expired running job."""

    async def update(
        self,
        job: DatasetValidationJob,
    ) -> None:
        """Stage updated durable-job lifecycle metadata."""


class JobClock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware time."""


class DatasetValidationJobUnitOfWork(Protocol):
    validation_jobs: DatasetValidationJobRepository

    async def __aenter__(
        self,
    ) -> "DatasetValidationJobUnitOfWork":
        """Enter one durable-job transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Rollback failed work and close the transaction."""

    async def commit(self) -> None:
        """Commit the durable-job transaction."""

    async def rollback(self) -> None:
        """Rollback the durable-job transaction."""
