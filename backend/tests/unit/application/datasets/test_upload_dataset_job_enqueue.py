from collections.abc import AsyncIterator
from datetime import UTC, datetime
from hashlib import sha256
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.datasets.ports import (
    DatasetObjectWriteResult,
)
from incrementality_api.application.datasets.upload_dataset import (
    UploadDataset,
    UploadDatasetCommand,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)
from incrementality_api.domain.jobs.status import (
    DatasetValidationJobStatus,
)

CONTENT = b"market,revenue\nnorth,250\n"
CHECKSUM = sha256(CONTENT).hexdigest()

CURRENT_TIME = datetime(
    2026,
    7,
    15,
    11,
    0,
    tzinfo=UTC,
)


async def content_chunks() -> AsyncIterator[bytes]:
    yield CONTENT[:8]
    yield CONTENT[8:]


class FixedClock:
    def now(self) -> datetime:
        return CURRENT_TIME


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


class FakeValidationJobRepository:
    def __init__(
        self,
        *,
        error: Exception | None = None,
    ) -> None:
        self._error = error
        self.added_jobs: list[DatasetValidationJob] = []

    async def add(
        self,
        job: DatasetValidationJob,
    ) -> None:
        if self._error is not None:
            raise self._error

        self.added_jobs.append(job)


class FakeUploadUnitOfWork:
    def __init__(
        self,
        dataset: Dataset,
        *,
        job_error: Exception | None = None,
    ) -> None:
        self.datasets = FakeDatasetRepository(dataset)
        self.validation_jobs = FakeValidationJobRepository(
            error=job_error,
        )
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
    def __init__(self) -> None:
        self.write_count = 0
        self.deleted_keys: list[str] = []
        self.received_content = b""

    async def write(
        self,
        *,
        storage_key: str,
        media_type: str,
        chunks: AsyncIterator[bytes],
    ) -> DatasetObjectWriteResult:
        del storage_key

        assert media_type == "text/csv"

        content = bytearray()

        async for chunk in chunks:
            content.extend(chunk)

        self.received_content = bytes(content)
        self.write_count += 1

        return DatasetObjectWriteResult(
            byte_size=len(self.received_content),
            checksum_sha256=sha256(self.received_content).hexdigest(),
        )

    def read(
        self,
        *,
        storage_key: str,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        del storage_key, chunk_size
        raise AssertionError("read must not be called")

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        self.deleted_keys.append(storage_key)


def build_pending_dataset() -> Dataset:
    return Dataset.register(
        workspace_id=uuid4(),
        project_id=uuid4(),
        created_by_user_id=uuid4(),
        source_filename="campaign-results.csv",
        storage_key=(
            f"workspaces/workspace-1/projects/project-1/datasets/{CHECKSUM}/campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=len(CONTENT),
        checksum_sha256=CHECKSUM,
    )


@pytest.mark.asyncio
async def test_upload_atomically_enqueues_validation_job() -> None:
    dataset = build_pending_dataset()
    unit_of_work = FakeUploadUnitOfWork(dataset)
    storage = FakeObjectStorage()

    result = await UploadDataset(
        unit_of_work=unit_of_work,
        object_storage=storage,
        clock=FixedClock(),
        validation_job_max_attempts=5,
    ).execute(
        UploadDatasetCommand(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            chunks=content_chunks(),
        )
    )

    assert storage.received_content == CONTENT
    assert unit_of_work.datasets.updated_datasets == [result]

    assert len(unit_of_work.validation_jobs.added_jobs) == 1

    job = unit_of_work.validation_jobs.added_jobs[0]

    assert job.workspace_id == dataset.workspace_id
    assert job.project_id == dataset.project_id
    assert job.dataset_id == dataset.id
    assert job.status is (DatasetValidationJobStatus.PENDING)
    assert job.attempt_count == 0
    assert job.max_attempts == 5
    assert job.created_at == CURRENT_TIME
    assert job.available_at == CURRENT_TIME

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_job_enqueue_failure_compensates_s3_object() -> None:
    dataset = build_pending_dataset()

    unit_of_work = FakeUploadUnitOfWork(
        dataset,
        job_error=RuntimeError("Validation job persistence failed."),
    )

    storage = FakeObjectStorage()

    with pytest.raises(
        RuntimeError,
        match="Validation job persistence failed",
    ):
        await UploadDataset(
            unit_of_work=unit_of_work,
            object_storage=storage,
            clock=FixedClock(),
            validation_job_max_attempts=3,
        ).execute(
            UploadDatasetCommand(
                workspace_id=dataset.workspace_id,
                project_id=dataset.project_id,
                dataset_id=dataset.id,
                chunks=content_chunks(),
            )
        )

    assert storage.write_count == 1
    assert storage.deleted_keys == [dataset.storage_key]

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


def test_rejects_nonpositive_validation_job_attempt_limit() -> None:
    dataset = build_pending_dataset()

    with pytest.raises(
        ValueError,
        match=("Validation job maximum attempts must be positive"),
    ):
        UploadDataset(
            unit_of_work=FakeUploadUnitOfWork(dataset),
            object_storage=FakeObjectStorage(),
            clock=FixedClock(),
            validation_job_max_attempts=0,
        )
