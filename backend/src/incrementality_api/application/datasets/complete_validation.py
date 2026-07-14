from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
)
from incrementality_api.application.datasets.ports import (
    DatasetClock,
    DatasetValidationUnitOfWork,
)
from incrementality_api.domain.datasets.entities import Dataset


@dataclass(frozen=True, slots=True)
class MarkDatasetReadyCommand:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    row_count: int
    column_count: int


@dataclass(frozen=True, slots=True)
class MarkDatasetFailedCommand:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    failure_reason: str


class MarkDatasetReady:
    """Persist successful dataset validation metadata."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetValidationUnitOfWork,
        clock: DatasetClock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(
        self,
        command: MarkDatasetReadyCommand,
    ) -> Dataset:
        async with self._unit_of_work:
            dataset = await self._unit_of_work.datasets.get_by_scope(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
            )

            if dataset is None:
                raise DatasetUnavailableError("Dataset is unavailable.")

            ready_dataset = dataset.mark_ready(
                validation_completed_at=self._clock.now(),
                row_count=command.row_count,
                column_count=command.column_count,
            )

            await self._unit_of_work.datasets.update(
                ready_dataset,
            )
            await self._unit_of_work.commit()

            return ready_dataset


class MarkDatasetFailed:
    """Persist failed dataset validation metadata."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetValidationUnitOfWork,
        clock: DatasetClock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(
        self,
        command: MarkDatasetFailedCommand,
    ) -> Dataset:
        async with self._unit_of_work:
            dataset = await self._unit_of_work.datasets.get_by_scope(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
            )

            if dataset is None:
                raise DatasetUnavailableError("Dataset is unavailable.")

            failed_dataset = dataset.mark_failed(
                validation_completed_at=self._clock.now(),
                failure_reason=command.failure_reason,
            )

            await self._unit_of_work.datasets.update(
                failed_dataset,
            )
            await self._unit_of_work.commit()

            return failed_dataset
