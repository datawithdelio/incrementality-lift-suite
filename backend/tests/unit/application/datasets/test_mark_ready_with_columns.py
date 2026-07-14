from datetime import UTC, datetime
from types import TracebackType
from uuid import uuid4

import pytest

from incrementality_api.application.datasets.complete_validation import (
    MarkDatasetReady,
    MarkDatasetReadyCommand,
)
from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

UPLOADED_AT = datetime(
    2026,
    7,
    14,
    13,
    0,
    tzinfo=UTC,
)

VALIDATION_STARTED_AT = datetime(
    2026,
    7,
    14,
    13,
    5,
    tzinfo=UTC,
)

VALIDATION_COMPLETED_AT = datetime(
    2026,
    7,
    14,
    13,
    7,
    tzinfo=UTC,
)


def build_validating_dataset() -> Dataset:
    return (
        Dataset.register(
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
        .mark_uploaded(
            uploaded_at=UPLOADED_AT,
        )
        .begin_validation(
            validation_started_at=VALIDATION_STARTED_AT,
        )
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
            missing_count=1,
        ),
    )


class FakeDatasetRepository:
    def __init__(
        self,
        dataset: Dataset | None,
    ) -> None:
        self._dataset = dataset
        self.updated_datasets: list[Dataset] = []

    async def get_by_scope(
        self,
        *,
        workspace_id,
        project_id,
        dataset_id,
    ) -> Dataset | None:
        del workspace_id, project_id, dataset_id
        return self._dataset

    async def update(
        self,
        dataset: Dataset,
    ) -> None:
        self.updated_datasets.append(dataset)


class FakeColumnRepository:
    def __init__(
        self,
        *,
        error: Exception | None = None,
    ) -> None:
        self._error = error
        self.replacements: list[
            tuple[
                object,
                tuple[DatasetColumnProfile, ...],
            ]
        ] = []

    async def replace_for_dataset(
        self,
        *,
        dataset_id,
        columns: tuple[
            DatasetColumnProfile,
            ...,
        ],
    ) -> None:
        if self._error is not None:
            raise self._error

        self.replacements.append(
            (
                dataset_id,
                columns,
            )
        )


class FakeValidationUnitOfWork:
    def __init__(
        self,
        *,
        dataset: Dataset | None,
        columns_error: Exception | None = None,
    ) -> None:
        self.datasets = FakeDatasetRepository(
            dataset,
        )
        self.columns = FakeColumnRepository(
            error=columns_error,
        )
        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ):
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback

        if exception_type is not None:
            self.rollback_count += 1

    async def commit(self) -> None:
        self.commit_count += 1


class FixedClock:
    def now(self) -> datetime:
        return VALIDATION_COMPLETED_AT


@pytest.mark.asyncio
async def test_marks_ready_and_replaces_columns_in_one_unit_of_work() -> None:
    dataset = build_validating_dataset()
    columns = build_columns()

    unit_of_work = FakeValidationUnitOfWork(
        dataset=dataset,
    )

    result = await MarkDatasetReady(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute(
        MarkDatasetReadyCommand(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            row_count=10,
            column_count=2,
            columns=columns,
        )
    )

    assert result.status is DatasetStatus.READY
    assert result.row_count == 10
    assert result.column_count == 2

    assert unit_of_work.columns.replacements == [
        (
            dataset.id,
            columns,
        )
    ]
    assert unit_of_work.datasets.updated_datasets == [
        result,
    ]
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_does_not_mark_ready_when_column_replacement_fails() -> None:
    dataset = build_validating_dataset()

    unit_of_work = FakeValidationUnitOfWork(
        dataset=dataset,
        columns_error=RuntimeError(
            "column write failed",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="column write failed",
    ):
        await MarkDatasetReady(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(
            MarkDatasetReadyCommand(
                workspace_id=dataset.workspace_id,
                project_id=dataset.project_id,
                dataset_id=dataset.id,
                row_count=10,
                column_count=2,
                columns=build_columns(),
            )
        )

    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_missing_dataset_does_not_replace_columns() -> None:
    unit_of_work = FakeValidationUnitOfWork(
        dataset=None,
    )

    with pytest.raises(
        DatasetUnavailableError,
        match="Dataset is unavailable",
    ):
        await MarkDatasetReady(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(
            MarkDatasetReadyCommand(
                workspace_id=uuid4(),
                project_id=uuid4(),
                dataset_id=uuid4(),
                row_count=10,
                column_count=2,
                columns=build_columns(),
            )
        )

    assert unit_of_work.columns.replacements == []
    assert unit_of_work.commit_count == 0
