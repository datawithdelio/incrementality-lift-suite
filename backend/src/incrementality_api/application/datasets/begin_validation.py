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
class BeginDatasetValidationCommand:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID


class BeginDatasetValidation:
    """Move one uploaded dataset into validation."""

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
        command: BeginDatasetValidationCommand,
    ) -> Dataset:
        async with self._unit_of_work:
            dataset = await self._unit_of_work.datasets.get_by_scope(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
            )

            if dataset is None:
                raise DatasetUnavailableError("Dataset is unavailable.")

            validating_dataset = dataset.begin_validation(
                validation_started_at=self._clock.now(),
            )

            await self._unit_of_work.datasets.update(
                validating_dataset,
            )
            await self._unit_of_work.commit()

            return validating_dataset
