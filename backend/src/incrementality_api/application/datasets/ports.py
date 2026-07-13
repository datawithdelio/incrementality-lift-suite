from types import TracebackType
from typing import Protocol
from uuid import UUID

from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.projects.entities import Project


class DatasetRepository(Protocol):
    async def add(
        self,
        dataset: Dataset,
    ) -> None:
        """Stage one dataset for persistence."""


class DatasetProjectReader(Protocol):
    async def get_by_id(
        self,
        project_id: UUID,
    ) -> Project | None:
        """Load the project receiving the dataset."""


class DatasetStorageKeyBuilder(Protocol):
    def build(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        source_filename: str,
        checksum_sha256: str,
    ) -> str:
        """Build an internal object-storage key."""


class DatasetUnitOfWork(Protocol):
    datasets: DatasetRepository
    projects: DatasetProjectReader

    async def __aenter__(
        self,
    ) -> "DatasetUnitOfWork":
        """Open the dataset transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back failures and close the transaction."""

    async def commit(self) -> None:
        """Commit the dataset transaction."""
