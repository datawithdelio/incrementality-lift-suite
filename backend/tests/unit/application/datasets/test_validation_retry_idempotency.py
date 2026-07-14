from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.datasets.begin_validation import (
    BeginDatasetValidation,
    BeginDatasetValidationCommand,
)
from incrementality_api.application.datasets.validate_dataset import (
    ValidateDataset,
    ValidateDatasetCommand,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

UPLOADED_AT = datetime(
    2026,
    7,
    15,
    17,
    0,
    tzinfo=UTC,
)

STARTED_AT = datetime(
    2026,
    7,
    15,
    17,
    1,
    tzinfo=UTC,
)

COMPLETED_AT = datetime(
    2026,
    7,
    15,
    17,
    2,
    tzinfo=UTC,
)


class FixedClock:
    def now(self) -> datetime:
        return COMPLETED_AT


class FakeDatasetRepository:
    def __init__(
        self,
        dataset: Dataset,
    ) -> None:
        self._dataset = dataset
        self.updated_datasets: list[Dataset] = []

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> Dataset | None:
        assert workspace_id == self._dataset.workspace_id
        assert project_id == self._dataset.project_id
        assert dataset_id == self._dataset.id

        return self._dataset

    async def update(
        self,
        dataset: Dataset,
    ) -> None:
        self.updated_datasets.append(dataset)


class FakeValidationUnitOfWork:
    def __init__(
        self,
        dataset: Dataset,
    ) -> None:
        self.datasets = FakeDatasetRepository(dataset)
        self.commit_count = 0

    async def __aenter__(
        self,
    ) -> "FakeValidationUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception, traceback

    async def commit(self) -> None:
        self.commit_count += 1


class FakeBeginValidation:
    def __init__(
        self,
        dataset: Dataset,
    ) -> None:
        self._dataset = dataset
        self.commands: list[BeginDatasetValidationCommand] = []

    async def execute(
        self,
        command: BeginDatasetValidationCommand,
    ) -> Dataset:
        self.commands.append(command)
        return self._dataset


class FailIfStorageIsRead:
    def read(
        self,
        *,
        storage_key: str,
        chunk_size: int,
    ) -> object:
        del storage_key, chunk_size

        raise AssertionError("Terminal dataset must not be read again.")


class FailIfValidatorRuns:
    async def validate(
        self,
        *,
        chunks: object,
    ) -> object:
        del chunks

        raise AssertionError("Terminal dataset must not be validated again.")


class FailIfCompletionRuns:
    async def execute(
        self,
        command: object,
    ) -> Dataset:
        del command

        raise AssertionError("Terminal dataset must not be completed again.")


def build_validating_dataset() -> Dataset:
    registered = Dataset.register(
        workspace_id=uuid4(),
        project_id=uuid4(),
        created_by_user_id=uuid4(),
        source_filename="campaign-results.csv",
        storage_key=(
            "workspaces/workspace-1/projects/project-1/datasets/dataset-1/campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=25,
        checksum_sha256="a" * 64,
    )

    uploaded = registered.mark_uploaded(
        uploaded_at=UPLOADED_AT,
    )

    return uploaded.begin_validation(
        validation_started_at=STARTED_AT,
    )


def build_ready_dataset() -> Dataset:
    return build_validating_dataset().mark_ready(
        validation_completed_at=COMPLETED_AT,
        row_count=1,
        column_count=2,
    )


def build_failed_dataset() -> Dataset:
    return build_validating_dataset().mark_failed(
        validation_completed_at=COMPLETED_AT,
        failure_reason="CSV content is malformed.",
    )


@pytest.mark.parametrize(
    "terminal_dataset",
    [
        build_ready_dataset(),
        build_failed_dataset(),
    ],
    ids=[
        "ready",
        "failed",
    ],
)
@pytest.mark.asyncio
async def test_begin_validation_is_idempotent_for_terminal_dataset(
    terminal_dataset: Dataset,
) -> None:
    unit_of_work = FakeValidationUnitOfWork(
        terminal_dataset,
    )

    result = await BeginDatasetValidation(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute(
        BeginDatasetValidationCommand(
            workspace_id=terminal_dataset.workspace_id,
            project_id=terminal_dataset.project_id,
            dataset_id=terminal_dataset.id,
        )
    )

    assert result == terminal_dataset
    assert result.status in {
        DatasetStatus.READY,
        DatasetStatus.FAILED,
    }
    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0


@pytest.mark.parametrize(
    "terminal_dataset",
    [
        build_ready_dataset(),
        build_failed_dataset(),
    ],
    ids=[
        "ready",
        "failed",
    ],
)
@pytest.mark.asyncio
async def test_validation_short_circuits_terminal_dataset(
    terminal_dataset: Dataset,
) -> None:
    result = await ValidateDataset(
        begin_validation=FakeBeginValidation(
            terminal_dataset,
        ),
        object_storage=FailIfStorageIsRead(),
        content_validator=FailIfValidatorRuns(),
        mark_ready=FailIfCompletionRuns(),
        mark_failed=FailIfCompletionRuns(),
    ).execute(
        ValidateDatasetCommand(
            workspace_id=terminal_dataset.workspace_id,
            project_id=terminal_dataset.project_id,
            dataset_id=terminal_dataset.id,
        )
    )

    assert result == terminal_dataset
