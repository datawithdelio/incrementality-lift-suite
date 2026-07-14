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
from incrementality_api.application.datasets.ports import (
    DatasetValidationResult,
)
from incrementality_api.application.datasets.validate_dataset import (
    ValidateDataset,
    ValidateDatasetCommand,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.domain.datasets.entities import Dataset

CONTENT = b"market,revenue\nnorth,250\n"

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


def build_columns() -> tuple[
    DatasetColumnProfile,
    ...,
]:
    return (
        DatasetColumnProfile(
            ordinal_position=1,
            source_name="market",
            normalized_name="market",
            inferred_type=DatasetColumnType.STRING,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=2,
            source_name="revenue",
            normalized_name="revenue",
            inferred_type=DatasetColumnType.INTEGER,
            nullable=False,
            missing_count=0,
        ),
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
    def read(
        self,
        *,
        storage_key: str,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        del storage_key, chunk_size

        async def chunks() -> AsyncIterator[bytes]:
            yield CONTENT

        return chunks()


class StubContentValidator:
    def __init__(
        self,
        result: DatasetValidationResult,
    ) -> None:
        self._result = result

    async def validate(
        self,
        *,
        chunks: AsyncIterator[bytes],
    ) -> DatasetValidationResult:
        async for _ in chunks:
            pass

        return self._result


class StubMarkReady:
    def __init__(self) -> None:
        self.commands: list[MarkDatasetReadyCommand] = []

    async def execute(
        self,
        command: MarkDatasetReadyCommand,
    ) -> Dataset:
        self.commands.append(command)
        dataset = build_validating_dataset()
        return dataset.mark_ready(
            validation_completed_at=datetime.now(UTC),
            row_count=command.row_count,
            column_count=command.column_count,
        )


class StubMarkFailed:
    def __init__(self) -> None:
        self.commands: list[MarkDatasetFailedCommand] = []

    async def execute(
        self,
        command: MarkDatasetFailedCommand,
    ) -> Dataset:
        self.commands.append(command)
        raise AssertionError("mark_failed must not be called")


@pytest.mark.asyncio
async def test_passes_discovered_columns_to_mark_ready() -> None:
    dataset = build_validating_dataset()
    columns = build_columns()
    mark_ready = StubMarkReady()

    await ValidateDataset(
        begin_validation=StubBeginValidation(dataset),
        object_storage=FakeObjectStorage(),
        content_validator=StubContentValidator(
            DatasetValidationResult(
                row_count=1,
                column_count=2,
                columns=columns,
            )
        ),
        mark_ready=mark_ready,
        mark_failed=StubMarkFailed(),
    ).execute(
        ValidateDatasetCommand(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
        )
    )

    assert mark_ready.commands == [
        MarkDatasetReadyCommand(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            row_count=1,
            column_count=2,
            columns=columns,
        )
    ]
