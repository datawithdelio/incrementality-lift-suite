from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
    DatasetUploadVerificationError,
)
from incrementality_api.application.datasets.ports import (
    DatasetClock,
    DatasetObjectStorage,
    DatasetObjectWriteResult,
    DatasetUploadUnitOfWork,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)


@dataclass(frozen=True, slots=True)
class UploadDatasetCommand:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    chunks: AsyncIterator[bytes]


class UploadDataset:
    """Upload, verify, and enqueue validation for a dataset."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetUploadUnitOfWork,
        object_storage: DatasetObjectStorage,
        clock: DatasetClock,
        validation_job_max_attempts: int = 3,
    ) -> None:
        if validation_job_max_attempts <= 0:
            raise ValueError("Validation job maximum attempts must be positive.")

        self._unit_of_work = unit_of_work
        self._object_storage = object_storage
        self._clock = clock
        self._validation_job_max_attempts = validation_job_max_attempts

    async def execute(
        self,
        command: UploadDatasetCommand,
    ) -> Dataset:
        async with self._unit_of_work:
            dataset = await self._unit_of_work.datasets.get_by_scope(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
            )

            if dataset is None:
                raise DatasetUnavailableError("Dataset is unavailable.")

            current_time = self._clock.now()

            uploaded_dataset = dataset.mark_uploaded(
                uploaded_at=current_time,
            )

            object_written = False

            try:
                write_result = await self._object_storage.write(
                    storage_key=dataset.storage_key,
                    media_type=dataset.media_type,
                    chunks=self._limit_chunks(
                        chunks=command.chunks,
                        maximum_bytes=dataset.byte_size,
                    ),
                )

                object_written = True

                self._verify_upload(
                    dataset=dataset,
                    write_result=write_result,
                )

                validation_job = DatasetValidationJob.enqueue(
                    workspace_id=dataset.workspace_id,
                    project_id=dataset.project_id,
                    dataset_id=dataset.id,
                    created_at=current_time,
                    available_at=current_time,
                    max_attempts=(self._validation_job_max_attempts),
                )

                await self._unit_of_work.datasets.update(
                    uploaded_dataset,
                )
                await self._unit_of_work.validation_jobs.add(
                    validation_job,
                )
                await self._unit_of_work.commit()
            except Exception:
                if object_written:
                    await self._object_storage.delete(
                        storage_key=dataset.storage_key,
                    )

                raise

            return uploaded_dataset

    @staticmethod
    async def _limit_chunks(
        *,
        chunks: AsyncIterator[bytes],
        maximum_bytes: int,
    ) -> AsyncIterator[bytes]:
        consumed_bytes = 0

        async for chunk in chunks:
            if not chunk:
                continue

            next_size = consumed_bytes + len(chunk)

            if next_size > maximum_bytes:
                raise DatasetUploadVerificationError(
                    "Uploaded dataset exceeds the registered byte size."
                )

            consumed_bytes = next_size
            yield chunk

    @staticmethod
    def _verify_upload(
        *,
        dataset: Dataset,
        write_result: DatasetObjectWriteResult,
    ) -> None:
        if write_result.byte_size != dataset.byte_size:
            raise DatasetUploadVerificationError(
                "Uploaded dataset byte size does not match the registered metadata."
            )

        if write_result.checksum_sha256.casefold() != dataset.checksum_sha256:
            raise DatasetUploadVerificationError(
                "Uploaded dataset checksum does not match the registered metadata."
            )
