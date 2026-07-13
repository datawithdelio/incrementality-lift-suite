from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.datasets.errors import (
    DatasetProjectUnavailableError,
    DatasetTooLargeError,
)
from incrementality_api.application.datasets.ports import (
    DatasetStorageKeyBuilder,
    DatasetUnitOfWork,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.validation import (
    normalize_dataset_checksum,
    normalize_dataset_filename,
    normalize_dataset_media_type,
    validate_dataset_byte_size,
)
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)

_PROJECT_UNAVAILABLE_MESSAGE = "Dataset project is unavailable."


@dataclass(frozen=True, slots=True)
class RegisterDatasetCommand:
    workspace_id: UUID
    project_id: UUID
    created_by_user_id: UUID
    source_filename: str
    media_type: str
    byte_size: int
    checksum_sha256: str


class RegisterDataset:
    """Register dataset metadata before object upload."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetUnitOfWork,
        storage_key_builder: DatasetStorageKeyBuilder,
        maximum_upload_bytes: int,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._storage_key_builder = storage_key_builder
        self._maximum_upload_bytes = maximum_upload_bytes

    async def execute(
        self,
        command: RegisterDatasetCommand,
    ) -> Dataset:
        source_filename = normalize_dataset_filename(
            command.source_filename,
        )
        media_type = normalize_dataset_media_type(
            command.media_type,
        )
        byte_size = validate_dataset_byte_size(
            command.byte_size,
        )
        checksum_sha256 = normalize_dataset_checksum(
            command.checksum_sha256,
        )

        if byte_size > self._maximum_upload_bytes:
            raise DatasetTooLargeError("Dataset exceeds the maximum upload size.")

        async with self._unit_of_work:
            project = await self._unit_of_work.projects.get_by_id(
                command.project_id,
            )

            if (
                project is None
                or project.workspace_id != command.workspace_id
                or project.status is not ProjectStatus.ACTIVE
            ):
                raise DatasetProjectUnavailableError(
                    _PROJECT_UNAVAILABLE_MESSAGE,
                )

            storage_key = self._storage_key_builder.build(
                workspace_id=command.workspace_id,
                project_id=project.id,
                source_filename=source_filename,
                checksum_sha256=checksum_sha256,
            )

            dataset = Dataset.register(
                workspace_id=command.workspace_id,
                project_id=project.id,
                created_by_user_id=command.created_by_user_id,
                source_filename=source_filename,
                storage_key=storage_key,
                media_type=media_type,
                byte_size=byte_size,
                checksum_sha256=checksum_sha256,
            )

            await self._unit_of_work.datasets.add(
                dataset,
            )
            await self._unit_of_work.commit()

            return dataset
