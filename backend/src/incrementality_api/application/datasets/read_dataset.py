from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
)
from incrementality_api.application.datasets.ports import (
    DatasetReadUnitOfWork,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
)
from incrementality_api.domain.datasets.entities import Dataset


@dataclass(frozen=True, slots=True)
class GetDatasetQuery:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID


class GetDataset:
    """Load one dataset inside its complete tenant scope."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetReadUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetDatasetQuery,
    ) -> Dataset:
        async with self._unit_of_work:
            dataset = await self._unit_of_work.datasets.get_by_scope_read(
                workspace_id=query.workspace_id,
                project_id=query.project_id,
                dataset_id=query.dataset_id,
            )

            if dataset is None:
                raise DatasetUnavailableError("Dataset is unavailable.")

            return dataset


@dataclass(frozen=True, slots=True)
class ListDatasetColumnsQuery:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID


class ListDatasetColumns:
    """List discovered columns for one scoped dataset."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetReadUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: ListDatasetColumnsQuery,
    ) -> tuple[
        DatasetColumnProfile,
        ...,
    ]:
        async with self._unit_of_work:
            dataset = await self._unit_of_work.datasets.get_by_scope_read(
                workspace_id=query.workspace_id,
                project_id=query.project_id,
                dataset_id=query.dataset_id,
            )

            if dataset is None:
                raise DatasetUnavailableError("Dataset is unavailable.")

            return await self._unit_of_work.columns.list_by_scope(
                workspace_id=query.workspace_id,
                project_id=query.project_id,
                dataset_id=query.dataset_id,
            )
