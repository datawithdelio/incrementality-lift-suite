from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
)
from incrementality_api.application.datasets.read_dataset import (
    GetDataset,
    GetDatasetQuery,
    ListDatasetColumns,
    ListDatasetColumnsQuery,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.domain.datasets.entities import Dataset


def build_dataset() -> Dataset:
    return Dataset.register(
        workspace_id=uuid4(),
        project_id=uuid4(),
        created_by_user_id=uuid4(),
        source_filename="campaign-results.csv",
        storage_key=(
            "workspaces/workspace-1/projects/project-1/datasets/checksum/campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=1024,
        checksum_sha256="a" * 64,
    )


def build_columns() -> tuple[
    DatasetColumnProfile,
    ...,
]:
    return (
        DatasetColumnProfile(
            ordinal_position=1,
            source_name="Market",
            normalized_name="market",
            inferred_type=DatasetColumnType.STRING,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=2,
            source_name="Revenue",
            normalized_name="revenue",
            inferred_type=DatasetColumnType.FLOAT,
            nullable=True,
            missing_count=2,
        ),
    )


class FakeDatasetRepository:
    def __init__(
        self,
        dataset: Dataset | None,
    ) -> None:
        self._dataset = dataset
        self.read_scopes: list[tuple[UUID, UUID, UUID]] = []

    async def get_by_scope_read(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> Dataset | None:
        self.read_scopes.append(
            (
                workspace_id,
                project_id,
                dataset_id,
            )
        )

        return self._dataset


class FakeDatasetColumnRepository:
    def __init__(
        self,
        columns: tuple[
            DatasetColumnProfile,
            ...,
        ] = (),
    ) -> None:
        self._columns = columns
        self.read_scopes: list[tuple[UUID, UUID, UUID]] = []

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
        self.read_scopes.append(
            (
                workspace_id,
                project_id,
                dataset_id,
            )
        )

        return self._columns


class FakeDatasetReadUnitOfWork:
    def __init__(
        self,
        *,
        dataset: Dataset | None,
        columns: tuple[
            DatasetColumnProfile,
            ...,
        ] = (),
    ) -> None:
        self.datasets = FakeDatasetRepository(
            dataset,
        )
        self.columns = FakeDatasetColumnRepository(
            columns,
        )
        self.enter_count = 0
        self.exit_count = 0

    async def __aenter__(
        self,
    ):
        self.enter_count += 1
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception, traceback
        self.exit_count += 1


@pytest.mark.asyncio
async def test_gets_dataset_without_a_write_transaction() -> None:
    dataset = build_dataset()

    unit_of_work = FakeDatasetReadUnitOfWork(
        dataset=dataset,
    )

    result = await GetDataset(
        unit_of_work=unit_of_work,
    ).execute(
        GetDatasetQuery(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
        )
    )

    assert result == dataset
    assert unit_of_work.datasets.read_scopes == [
        (
            dataset.workspace_id,
            dataset.project_id,
            dataset.id,
        )
    ]
    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1


@pytest.mark.asyncio
async def test_get_dataset_rejects_unknown_scope() -> None:
    unit_of_work = FakeDatasetReadUnitOfWork(
        dataset=None,
    )

    with pytest.raises(
        DatasetUnavailableError,
        match="Dataset is unavailable",
    ):
        await GetDataset(
            unit_of_work=unit_of_work,
        ).execute(
            GetDatasetQuery(
                workspace_id=uuid4(),
                project_id=uuid4(),
                dataset_id=uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_lists_dataset_columns_in_repository_order() -> None:
    dataset = build_dataset()
    columns = build_columns()

    unit_of_work = FakeDatasetReadUnitOfWork(
        dataset=dataset,
        columns=columns,
    )

    result = await ListDatasetColumns(
        unit_of_work=unit_of_work,
    ).execute(
        ListDatasetColumnsQuery(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
        )
    )

    assert result == columns
    assert unit_of_work.columns.read_scopes == [
        (
            dataset.workspace_id,
            dataset.project_id,
            dataset.id,
        )
    ]


@pytest.mark.asyncio
async def test_missing_dataset_does_not_query_columns() -> None:
    unit_of_work = FakeDatasetReadUnitOfWork(
        dataset=None,
        columns=build_columns(),
    )

    with pytest.raises(
        DatasetUnavailableError,
        match="Dataset is unavailable",
    ):
        await ListDatasetColumns(
            unit_of_work=unit_of_work,
        ).execute(
            ListDatasetColumnsQuery(
                workspace_id=uuid4(),
                project_id=uuid4(),
                dataset_id=uuid4(),
            )
        )

    assert unit_of_work.columns.read_scopes == []
