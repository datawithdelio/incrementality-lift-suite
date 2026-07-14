from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.datasets.begin_validation import (
    BeginDatasetValidation,
    BeginDatasetValidationCommand,
)
from incrementality_api.application.datasets.complete_validation import (
    MarkDatasetFailed,
    MarkDatasetFailedCommand,
    MarkDatasetReady,
    MarkDatasetReadyCommand,
)
from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetTransitionError,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

UPLOADED_AT = datetime(
    2026,
    7,
    15,
    9,
    0,
    tzinfo=UTC,
)

VALIDATION_STARTED_AT = datetime(
    2026,
    7,
    15,
    9,
    5,
    tzinfo=UTC,
)

VALIDATION_COMPLETED_AT = datetime(
    2026,
    7,
    15,
    9,
    7,
    tzinfo=UTC,
)


class FixedClock:
    def __init__(
        self,
        current_time: datetime,
    ) -> None:
        self._current_time = current_time

    def now(self) -> datetime:
        return self._current_time


class FakeDatasetRepository:
    def __init__(
        self,
        dataset: Dataset | None,
    ) -> None:
        self._dataset = dataset
        self.updated_datasets: list[Dataset] = []
        self.received_scope: tuple[UUID, UUID, UUID] | None = None

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> Dataset | None:
        self.received_scope = (
            workspace_id,
            project_id,
            dataset_id,
        )
        return self._dataset

    async def update(
        self,
        dataset: Dataset,
    ) -> None:
        self.updated_datasets.append(dataset)


class FakeValidationUnitOfWork:
    def __init__(
        self,
        dataset: Dataset | None,
    ) -> None:
        self.datasets = FakeDatasetRepository(dataset)
        self.commit_count = 0
        self.rollback_count = 0

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
        del exception, traceback

        if exception_type is not None:
            self.rollback_count += 1

    async def commit(self) -> None:
        self.commit_count += 1


def build_pending_dataset() -> Dataset:
    return Dataset.register(
        workspace_id=uuid4(),
        project_id=uuid4(),
        created_by_user_id=uuid4(),
        source_filename="campaign-results.csv",
        storage_key=(
            "workspaces/workspace-1/projects/project-1/datasets/checksum/campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=1_024,
        checksum_sha256="a" * 64,
    )


def build_uploaded_dataset() -> Dataset:
    return build_pending_dataset().mark_uploaded(
        uploaded_at=UPLOADED_AT,
    )


def build_validating_dataset() -> Dataset:
    return build_uploaded_dataset().begin_validation(
        validation_started_at=VALIDATION_STARTED_AT,
    )


@pytest.mark.asyncio
async def test_begins_dataset_validation() -> None:
    dataset = build_uploaded_dataset()
    unit_of_work = FakeValidationUnitOfWork(dataset)

    result = await BeginDatasetValidation(
        unit_of_work=unit_of_work,
        clock=FixedClock(VALIDATION_STARTED_AT),
    ).execute(
        BeginDatasetValidationCommand(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
        )
    )

    assert result.status is DatasetStatus.VALIDATING
    assert result.validation_started_at == VALIDATION_STARTED_AT

    assert unit_of_work.datasets.received_scope == (
        dataset.workspace_id,
        dataset.project_id,
        dataset.id,
    )
    assert unit_of_work.datasets.updated_datasets == [result]
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_begin_validation_rejects_unavailable_dataset() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    unit_of_work = FakeValidationUnitOfWork(None)

    with pytest.raises(
        DatasetUnavailableError,
        match="Dataset is unavailable",
    ):
        await BeginDatasetValidation(
            unit_of_work=unit_of_work,
            clock=FixedClock(VALIDATION_STARTED_AT),
        ).execute(
            BeginDatasetValidationCommand(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
            )
        )

    assert unit_of_work.datasets.received_scope == (
        workspace_id,
        project_id,
        dataset_id,
    )
    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_begin_validation_rejects_invalid_state() -> None:
    dataset = build_pending_dataset()
    unit_of_work = FakeValidationUnitOfWork(dataset)

    with pytest.raises(
        InvalidDatasetTransitionError,
        match="cannot begin validation",
    ):
        await BeginDatasetValidation(
            unit_of_work=unit_of_work,
            clock=FixedClock(VALIDATION_STARTED_AT),
        ).execute(
            BeginDatasetValidationCommand(
                workspace_id=dataset.workspace_id,
                project_id=dataset.project_id,
                dataset_id=dataset.id,
            )
        )

    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_marks_validating_dataset_ready() -> None:
    dataset = build_validating_dataset()
    unit_of_work = FakeValidationUnitOfWork(dataset)

    result = await MarkDatasetReady(
        unit_of_work=unit_of_work,
        clock=FixedClock(VALIDATION_COMPLETED_AT),
    ).execute(
        MarkDatasetReadyCommand(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            row_count=250,
            column_count=8,
        )
    )

    assert result.status is DatasetStatus.READY
    assert result.row_count == 250
    assert result.column_count == 8
    assert result.validation_completed_at == VALIDATION_COMPLETED_AT

    assert unit_of_work.datasets.updated_datasets == [result]
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_marks_validating_dataset_failed() -> None:
    dataset = build_validating_dataset()
    unit_of_work = FakeValidationUnitOfWork(dataset)

    result = await MarkDatasetFailed(
        unit_of_work=unit_of_work,
        clock=FixedClock(VALIDATION_COMPLETED_AT),
    ).execute(
        MarkDatasetFailedCommand(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            failure_reason=("CSV contains duplicate column names."),
        )
    )

    assert result.status is DatasetStatus.FAILED
    assert result.failure_reason == ("CSV contains duplicate column names.")
    assert result.validation_completed_at == VALIDATION_COMPLETED_AT

    assert unit_of_work.datasets.updated_datasets == [result]
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_mark_ready_rejects_unavailable_dataset() -> None:
    unit_of_work = FakeValidationUnitOfWork(None)

    with pytest.raises(
        DatasetUnavailableError,
        match="Dataset is unavailable",
    ):
        await MarkDatasetReady(
            unit_of_work=unit_of_work,
            clock=FixedClock(VALIDATION_COMPLETED_AT),
        ).execute(
            MarkDatasetReadyCommand(
                workspace_id=uuid4(),
                project_id=uuid4(),
                dataset_id=uuid4(),
                row_count=250,
                column_count=8,
            )
        )

    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_mark_failed_rejects_invalid_state() -> None:
    dataset = build_uploaded_dataset()
    unit_of_work = FakeValidationUnitOfWork(dataset)

    with pytest.raises(
        InvalidDatasetTransitionError,
        match="cannot be marked failed",
    ):
        await MarkDatasetFailed(
            unit_of_work=unit_of_work,
            clock=FixedClock(VALIDATION_COMPLETED_AT),
        ).execute(
            MarkDatasetFailedCommand(
                workspace_id=dataset.workspace_id,
                project_id=dataset.project_id,
                dataset_id=dataset.id,
                failure_reason="Malformed CSV.",
            )
        )

    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1
