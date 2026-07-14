from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest

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
    DatasetValidationResult,
)
from incrementality_api.application.datasets.validate_dataset import (
    ValidateDataset,
    ValidateDatasetCommand,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

CONTENT = b"market,revenue\nnorth,250\nsouth,175\n"

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
            byte_size=len(CONTENT),
            checksum_sha256="a" * 64,
        )
        .mark_uploaded(
            uploaded_at=UPLOADED_AT,
        )
        .begin_validation(
            validation_started_at=VALIDATION_STARTED_AT,
        )
    )


class StubBeginValidation:
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


class FakeObjectStorage:
    def __init__(
        self,
        *,
        error: Exception | None = None,
    ) -> None:
        self._error = error
        self.read_calls: list[tuple[str, int]] = []

    def read(
        self,
        *,
        storage_key: str,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        self.read_calls.append(
            (
                storage_key,
                chunk_size,
            )
        )

        async def chunks() -> AsyncIterator[bytes]:
            if self._error is not None:
                raise self._error

            yield CONTENT[:7]
            yield CONTENT[7:]

        return chunks()

    async def write(
        self,
        *,
        storage_key: str,
        media_type: str,
        chunks: AsyncIterator[bytes],
    ) -> object:
        del storage_key, media_type, chunks
        raise AssertionError("write must not be called")

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        del storage_key
        raise AssertionError("delete must not be called")


class StubContentValidator:
    def __init__(
        self,
        *,
        result: DatasetValidationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_content = b""

    async def validate(
        self,
        *,
        chunks: AsyncIterator[bytes],
    ) -> DatasetValidationResult:
        content = bytearray()

        async for chunk in chunks:
            content.extend(chunk)

        self.received_content = bytes(content)

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Validation result was not configured.")

        return self._result


class StubMarkReady:
    def __init__(
        self,
        result: Dataset,
    ) -> None:
        self._result = result
        self.commands: list[MarkDatasetReadyCommand] = []

    async def execute(
        self,
        command: MarkDatasetReadyCommand,
    ) -> Dataset:
        self.commands.append(command)
        return self._result


class StubMarkFailed:
    def __init__(
        self,
        result: Dataset,
    ) -> None:
        self._result = result
        self.commands: list[MarkDatasetFailedCommand] = []

    async def execute(
        self,
        command: MarkDatasetFailedCommand,
    ) -> Dataset:
        self.commands.append(command)
        return self._result


def command_for(
    dataset: Dataset,
) -> ValidateDatasetCommand:
    return ValidateDatasetCommand(
        workspace_id=dataset.workspace_id,
        project_id=dataset.project_id,
        dataset_id=dataset.id,
    )


@pytest.mark.asyncio
async def test_validates_object_and_marks_dataset_ready() -> None:
    dataset = build_validating_dataset()

    ready_dataset = dataset.mark_ready(
        validation_completed_at=VALIDATION_COMPLETED_AT,
        row_count=2,
        column_count=2,
    )

    begin = StubBeginValidation(dataset)
    storage = FakeObjectStorage()
    validator = StubContentValidator(
        result=DatasetValidationResult(
            row_count=2,
            column_count=2,
        )
    )
    mark_ready = StubMarkReady(ready_dataset)
    mark_failed = StubMarkFailed(dataset)

    result = await ValidateDataset(
        begin_validation=begin,
        object_storage=storage,
        content_validator=validator,
        mark_ready=mark_ready,
        mark_failed=mark_failed,
        read_chunk_size=7,
    ).execute(command_for(dataset))

    assert result is ready_dataset
    assert result.status is DatasetStatus.READY

    assert storage.read_calls == [
        (
            dataset.storage_key,
            7,
        )
    ]
    assert validator.received_content == CONTENT

    assert mark_ready.commands == [
        MarkDatasetReadyCommand(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            row_count=2,
            column_count=2,
        )
    ]
    assert mark_failed.commands == []


@pytest.mark.asyncio
async def test_invalid_content_marks_dataset_failed() -> None:
    dataset = build_validating_dataset()

    failed_dataset = dataset.mark_failed(
        validation_completed_at=VALIDATION_COMPLETED_AT,
        failure_reason="CSV column names must be unique.",
    )

    mark_ready = StubMarkReady(dataset)
    mark_failed = StubMarkFailed(failed_dataset)

    result = await ValidateDataset(
        begin_validation=StubBeginValidation(dataset),
        object_storage=FakeObjectStorage(),
        content_validator=StubContentValidator(
            error=DatasetContentValidationError("CSV column names must be unique.")
        ),
        mark_ready=mark_ready,
        mark_failed=mark_failed,
    ).execute(command_for(dataset))

    assert result is failed_dataset
    assert result.status is DatasetStatus.FAILED

    assert mark_ready.commands == []
    assert mark_failed.commands == [
        MarkDatasetFailedCommand(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            failure_reason=("CSV column names must be unique."),
        )
    ]


@pytest.mark.asyncio
async def test_infrastructure_failure_remains_retryable() -> None:
    dataset = build_validating_dataset()

    mark_ready = StubMarkReady(dataset)
    mark_failed = StubMarkFailed(dataset)

    with pytest.raises(
        RuntimeError,
        match="S3 temporarily unavailable",
    ):
        await ValidateDataset(
            begin_validation=StubBeginValidation(dataset),
            object_storage=FakeObjectStorage(error=RuntimeError("S3 temporarily unavailable.")),
            content_validator=StubContentValidator(
                result=DatasetValidationResult(
                    row_count=2,
                    column_count=2,
                )
            ),
            mark_ready=mark_ready,
            mark_failed=mark_failed,
        ).execute(command_for(dataset))

    assert mark_ready.commands == []
    assert mark_failed.commands == []


def test_rejects_nonpositive_read_chunk_size() -> None:
    dataset = build_validating_dataset()

    with pytest.raises(
        ValueError,
        match="Validation read chunk size must be positive",
    ):
        ValidateDataset(
            begin_validation=StubBeginValidation(dataset),
            object_storage=FakeObjectStorage(),
            content_validator=StubContentValidator(
                result=DatasetValidationResult(
                    row_count=2,
                    column_count=2,
                )
            ),
            mark_ready=StubMarkReady(dataset),
            mark_failed=StubMarkFailed(dataset),
            read_chunk_size=0,
        )
