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
    DatasetUploadUnitOfWork,
)
from incrementality_api.domain.datasets.entities import Dataset


@dataclass(frozen=True, slots=True)
class UploadDatasetCommand:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    chunks: AsyncIterator[bytes]


class UploadDataset:
    """Upload and verify bytes for registered dataset metadata."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetUploadUnitOfWork,
        object_storage: DatasetObjectStorage,
        clock: DatasetClock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._object_storage = object_storage
        self._clock = clock

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

            # Validate the lifecycle transition before writing bytes.
            uploaded_dataset = dataset.mark_uploaded(
                uploaded_at=self._clock.now(),
            )

            write_result = await self._object_storage.write(
                storage_key=dataset.storage_key,
                media_type=dataset.media_type,
                chunks=command.chunks,
            )

            if write_result.byte_size != dataset.byte_size:
                await self._object_storage.delete(
                    storage_key=dataset.storage_key,
                )

                raise DatasetUploadVerificationError(
                    "Uploaded dataset byte size does not match the registered metadata."
                )

            if write_result.checksum_sha256.casefold() != dataset.checksum_sha256:
                await self._object_storage.delete(
                    storage_key=dataset.storage_key,
                )

                raise DatasetUploadVerificationError(
                    "Uploaded dataset checksum does not match the registered metadata."
                )

            await self._unit_of_work.datasets.update(
                uploaded_dataset,
            )
            await self._unit_of_work.commit()

            return uploaded_dataset
