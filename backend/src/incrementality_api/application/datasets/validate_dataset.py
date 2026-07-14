from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from incrementality_api.application.datasets.begin_validation import (
    BeginDatasetValidationCommand,
)
from incrementality_api.application.datasets.complete_validation import (
    MarkDatasetFailedCommand,
    MarkDatasetReadyCommand,
)
from incrementality_api.application.datasets.errors import (
    DatasetContentValidationError,
)
from incrementality_api.application.datasets.ports import (
    DatasetContentValidator,
    DatasetObjectStorage,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)


class BeginValidationAction(Protocol):
    async def execute(
        self,
        command: BeginDatasetValidationCommand,
    ) -> Dataset:
        """Start or resume dataset validation."""


class MarkReadyAction(Protocol):
    async def execute(
        self,
        command: MarkDatasetReadyCommand,
    ) -> Dataset:
        """Complete successful validation."""


class MarkFailedAction(Protocol):
    async def execute(
        self,
        command: MarkDatasetFailedCommand,
    ) -> Dataset:
        """Complete failed validation."""


@dataclass(frozen=True, slots=True)
class ValidateDatasetCommand:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID


class ValidateDataset:
    """Validate an uploaded dataset outside database transactions."""

    def __init__(
        self,
        *,
        begin_validation: BeginValidationAction,
        object_storage: DatasetObjectStorage,
        content_validator: DatasetContentValidator,
        mark_ready: MarkReadyAction,
        mark_failed: MarkFailedAction,
        read_chunk_size: int = 1024 * 1024,
    ) -> None:
        if read_chunk_size <= 0:
            raise ValueError("Validation read chunk size must be positive.")

        self._begin_validation = begin_validation
        self._object_storage = object_storage
        self._content_validator = content_validator
        self._mark_ready = mark_ready
        self._mark_failed = mark_failed
        self._read_chunk_size = read_chunk_size

    async def execute(
        self,
        command: ValidateDatasetCommand,
    ) -> Dataset:
        validating_dataset = await self._begin_validation.execute(
            BeginDatasetValidationCommand(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
            )
        )

        if validating_dataset.status in {
            DatasetStatus.READY,
            DatasetStatus.FAILED,
        }:
            return validating_dataset

        chunks = self._object_storage.read(
            storage_key=validating_dataset.storage_key,
            chunk_size=self._read_chunk_size,
        )

        try:
            validation_result = await self._content_validator.validate(
                chunks=chunks,
            )
        except DatasetContentValidationError as error:
            return await self._mark_failed.execute(
                MarkDatasetFailedCommand(
                    workspace_id=command.workspace_id,
                    project_id=command.project_id,
                    dataset_id=command.dataset_id,
                    failure_reason=str(error),
                )
            )

        return await self._mark_ready.execute(
            MarkDatasetReadyCommand(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
                row_count=validation_result.row_count,
                column_count=(validation_result.column_count),
            )
        )
