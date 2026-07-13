from collections.abc import AsyncIterator
from datetime import UTC, datetime
from hashlib import sha256
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
    DatasetUploadVerificationError,
)
from incrementality_api.application.datasets.ports import (
    DatasetObjectWriteResult,
)
from incrementality_api.application.datasets.upload_dataset import (
    UploadDataset,
    UploadDatasetCommand,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetTransitionError,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

CONTENT = b"market,revenue\nnorth,250\n"
CONTENT_SIZE = len(CONTENT)
CONTENT_CHECKSUM = sha256(CONTENT).hexdigest()

UPLOADED_AT = datetime(
    2026,
    7,
    14,
    14,
    0,
    tzinfo=UTC,
)


async def content_chunks() -> AsyncIterator[bytes]:
    yield CONTENT[:8]
    yield CONTENT[8:18]
    yield CONTENT[18:]


class FixedClock:
    def now(self) -> datetime:
        return UPLOADED_AT


class FakeUploadRepository:
    def __init__(
        self,
        dataset: Dataset | None,
    ) -> None:
        self._dataset = dataset
        self.updated_datasets: list[Dataset] = []
        self.requested_scope: tuple[UUID, UUID, UUID] | None = None

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> Dataset | None:
        self.requested_scope = (
            workspace_id,
            project_id,
            dataset_id,
        )

        if self._dataset is None:
            return None

        if (
            self._dataset.workspace_id != workspace_id
            or self._dataset.project_id != project_id
            or self._dataset.id != dataset_id
        ):
            return None

        return self._dataset

    async def update(
        self,
        dataset: Dataset,
    ) -> None:
        self.updated_datasets.append(dataset)


class FakeUploadUnitOfWork:
    def __init__(
        self,
        dataset: Dataset | None,
    ) -> None:
        self.datasets = FakeUploadRepository(dataset)
        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeUploadUnitOfWork":
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


class FakeObjectStorage:
    def __init__(
        self,
        *,
        reported_byte_size: int | None = None,
        reported_checksum: str | None = None,
    ) -> None:
        self._reported_byte_size = reported_byte_size
        self._reported_checksum = reported_checksum
        self.write_count = 0
        self.written_key: str | None = None
        self.written_media_type: str | None = None
        self.received_content = b""
        self.deleted_keys: list[str] = []

    async def write(
        self,
        *,
        storage_key: str,
        media_type: str,
        chunks: AsyncIterator[bytes],
    ) -> DatasetObjectWriteResult:
        self.write_count += 1
        self.written_key = storage_key
        self.written_media_type = media_type

        received = bytearray()

        async for chunk in chunks:
            received.extend(chunk)

        self.received_content = bytes(received)

        return DatasetObjectWriteResult(
            byte_size=(
                self._reported_byte_size
                if self._reported_byte_size is not None
                else len(self.received_content)
            ),
            checksum_sha256=(
                self._reported_checksum
                if self._reported_checksum is not None
                else sha256(self.received_content).hexdigest()
            ),
        )

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        self.deleted_keys.append(storage_key)


def build_pending_dataset() -> Dataset:
    workspace_id = uuid4()
    project_id = uuid4()

    return Dataset.register(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=uuid4(),
        source_filename="campaign-results.csv",
        storage_key=(
            f"workspaces/{workspace_id}/"
            f"projects/{project_id}/"
            f"datasets/{CONTENT_CHECKSUM}/"
            "campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=CONTENT_SIZE,
        checksum_sha256=CONTENT_CHECKSUM,
    )


def build_command(
    dataset: Dataset,
) -> UploadDatasetCommand:
    return UploadDatasetCommand(
        workspace_id=dataset.workspace_id,
        project_id=dataset.project_id,
        dataset_id=dataset.id,
        chunks=content_chunks(),
    )


@pytest.mark.asyncio
async def test_uploads_verifies_and_marks_dataset_uploaded() -> None:
    dataset = build_pending_dataset()
    unit_of_work = FakeUploadUnitOfWork(dataset)
    object_storage = FakeObjectStorage()

    result = await UploadDataset(
        unit_of_work=unit_of_work,
        object_storage=object_storage,
        clock=FixedClock(),
    ).execute(
        build_command(dataset),
    )

    assert result.status is DatasetStatus.UPLOADED
    assert result.uploaded_at == UPLOADED_AT

    assert object_storage.write_count == 1
    assert object_storage.written_key == dataset.storage_key
    assert object_storage.written_media_type == dataset.media_type
    assert object_storage.received_content == CONTENT
    assert object_storage.deleted_keys == []

    assert unit_of_work.datasets.updated_datasets == [
        result,
    ]
    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_rejects_unavailable_or_cross_scope_dataset() -> None:
    dataset = build_pending_dataset()
    unit_of_work = FakeUploadUnitOfWork(dataset)
    object_storage = FakeObjectStorage()

    command = UploadDatasetCommand(
        workspace_id=uuid4(),
        project_id=dataset.project_id,
        dataset_id=dataset.id,
        chunks=content_chunks(),
    )

    with pytest.raises(
        DatasetUnavailableError,
        match="Dataset is unavailable",
    ):
        await UploadDataset(
            unit_of_work=unit_of_work,
            object_storage=object_storage,
            clock=FixedClock(),
        ).execute(command)

    assert object_storage.write_count == 0
    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_checksum_mismatch_deletes_object_and_rolls_back() -> None:
    dataset = build_pending_dataset()
    unit_of_work = FakeUploadUnitOfWork(dataset)
    object_storage = FakeObjectStorage(
        reported_checksum="f" * 64,
    )

    with pytest.raises(
        DatasetUploadVerificationError,
        match="checksum",
    ):
        await UploadDataset(
            unit_of_work=unit_of_work,
            object_storage=object_storage,
            clock=FixedClock(),
        ).execute(
            build_command(dataset),
        )

    assert object_storage.deleted_keys == [
        dataset.storage_key,
    ]
    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_size_mismatch_deletes_object_and_rolls_back() -> None:
    dataset = build_pending_dataset()
    unit_of_work = FakeUploadUnitOfWork(dataset)
    object_storage = FakeObjectStorage(
        reported_byte_size=CONTENT_SIZE + 1,
    )

    with pytest.raises(
        DatasetUploadVerificationError,
        match="byte size",
    ):
        await UploadDataset(
            unit_of_work=unit_of_work,
            object_storage=object_storage,
            clock=FixedClock(),
        ).execute(
            build_command(dataset),
        )

    assert object_storage.deleted_keys == [
        dataset.storage_key,
    ]
    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_repeated_upload_is_rejected_before_storage() -> None:
    dataset = build_pending_dataset().mark_uploaded(
        uploaded_at=UPLOADED_AT,
    )

    unit_of_work = FakeUploadUnitOfWork(dataset)
    object_storage = FakeObjectStorage()

    with pytest.raises(
        InvalidDatasetTransitionError,
        match="cannot be marked uploaded",
    ):
        await UploadDataset(
            unit_of_work=unit_of_work,
            object_storage=object_storage,
            clock=FixedClock(),
        ).execute(
            build_command(dataset),
        )

    assert object_storage.write_count == 0
    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


class FailingUpdateRepository(
    FakeUploadRepository,
):
    async def update(
        self,
        dataset: Dataset,
    ) -> None:
        del dataset

        raise RuntimeError("Dataset update failed.")


class FailingUpdateUnitOfWork(
    FakeUploadUnitOfWork,
):
    def __init__(
        self,
        dataset: Dataset,
    ) -> None:
        super().__init__(dataset)

        self.datasets = FailingUpdateRepository(
            dataset,
        )


class FailingCommitUnitOfWork(
    FakeUploadUnitOfWork,
):
    async def commit(self) -> None:
        self.commit_count += 1

        raise RuntimeError("Dataset commit failed.")


@pytest.mark.asyncio
async def test_update_failure_deletes_uploaded_object() -> None:
    dataset = build_pending_dataset()
    unit_of_work = FailingUpdateUnitOfWork(
        dataset,
    )
    object_storage = FakeObjectStorage()

    with pytest.raises(
        RuntimeError,
        match="Dataset update failed",
    ):
        await UploadDataset(
            unit_of_work=unit_of_work,
            object_storage=object_storage,
            clock=FixedClock(),
        ).execute(
            build_command(dataset),
        )

    assert object_storage.write_count == 1
    assert object_storage.deleted_keys == [
        dataset.storage_key,
    ]

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_commit_failure_deletes_uploaded_object() -> None:
    dataset = build_pending_dataset()
    unit_of_work = FailingCommitUnitOfWork(
        dataset,
    )
    object_storage = FakeObjectStorage()

    with pytest.raises(
        RuntimeError,
        match="Dataset commit failed",
    ):
        await UploadDataset(
            unit_of_work=unit_of_work,
            object_storage=object_storage,
            clock=FixedClock(),
        ).execute(
            build_command(dataset),
        )

    assert object_storage.write_count == 1
    assert object_storage.deleted_keys == [
        dataset.storage_key,
    ]

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 1


async def oversized_content_chunks() -> AsyncIterator[bytes]:
    yield CONTENT
    yield b"unexpected-extra-content"


@pytest.mark.asyncio
async def test_stops_stream_when_content_exceeds_registered_size() -> None:
    dataset = build_pending_dataset()
    unit_of_work = FakeUploadUnitOfWork(dataset)
    object_storage = FakeObjectStorage()

    command = UploadDatasetCommand(
        workspace_id=dataset.workspace_id,
        project_id=dataset.project_id,
        dataset_id=dataset.id,
        chunks=oversized_content_chunks(),
    )

    with pytest.raises(
        DatasetUploadVerificationError,
        match="exceeds the registered byte size",
    ):
        await UploadDataset(
            unit_of_work=unit_of_work,
            object_storage=object_storage,
            clock=FixedClock(),
        ).execute(command)

    # Storage was invoked, but its write never completed.
    assert object_storage.write_count == 1
    assert object_storage.received_content == b""

    # No complete object exists, so compensation deletion is unnecessary.
    assert object_storage.deleted_keys == []

    assert unit_of_work.datasets.updated_datasets == []
    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1
