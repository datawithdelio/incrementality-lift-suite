from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol
from uuid import UUID

from incrementality_api.application.jobs.ports import (
    DatasetValidationJobRepository,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.projects.entities import Project


class DatasetRepository(Protocol):
    async def add(
        self,
        dataset: Dataset,
    ) -> None:
        """Stage one dataset for persistence."""

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> Dataset | None:
        """Load and lock one dataset within tenant scope."""

    async def get_by_scope_read(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> Dataset | None:
        """Load one dataset without acquiring a write lock."""

    async def update(
        self,
        dataset: Dataset,
    ) -> None:
        """Stage updated dataset lifecycle metadata."""


class DatasetColumnRepository(Protocol):
    async def replace_for_dataset(
        self,
        *,
        dataset_id: UUID,
        columns: tuple[
            DatasetColumnProfile,
            ...,
        ],
    ) -> None:
        """Replace the discovered columns for one dataset."""

    async def list_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> tuple[
        DatasetColumnProfile,
        ...,
    ]:
        """List columns within complete dataset tenant scope."""


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


class DatasetReadUnitOfWork(Protocol):
    datasets: DatasetRepository
    columns: DatasetColumnRepository

    async def __aenter__(
        self,
    ) -> "DatasetReadUnitOfWork":
        """Open one read-scoped database session."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the read-scoped database session."""


class DatasetUploadUnitOfWork(Protocol):
    datasets: DatasetRepository
    validation_jobs: DatasetValidationJobRepository

    async def __aenter__(
        self,
    ) -> "DatasetUploadUnitOfWork":
        """Open the upload metadata transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back failures and close the transaction."""

    async def commit(self) -> None:
        """Commit updated dataset metadata."""


@dataclass(frozen=True, slots=True)
class DatasetObjectWriteResult:
    byte_size: int
    checksum_sha256: str


class DatasetObjectStorage(Protocol):
    async def write(
        self,
        *,
        storage_key: str,
        media_type: str,
        chunks: AsyncIterator[bytes],
    ) -> DatasetObjectWriteResult:
        """Stream an object and return server-computed metadata."""

    def read(
        self,
        *,
        storage_key: str,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        """Read an object through bounded asynchronous chunks."""

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        """Delete an uploaded object."""


class DatasetClock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware timestamp."""


class DatasetValidationUnitOfWork(Protocol):
    datasets: DatasetRepository
    columns: DatasetColumnRepository

    async def __aenter__(
        self,
    ) -> "DatasetValidationUnitOfWork":
        """Open one validation lifecycle transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back failures and close the transaction."""

    async def commit(self) -> None:
        """Commit updated validation lifecycle metadata."""


@dataclass(frozen=True, slots=True)
class DatasetValidationResult:
    row_count: int
    column_count: int
    columns: tuple[DatasetColumnProfile, ...] = ()


class DatasetContentValidator(Protocol):
    async def validate(
        self,
        *,
        chunks: AsyncIterator[bytes],
    ) -> DatasetValidationResult:
        """Validate dataset content and return structural metadata."""
