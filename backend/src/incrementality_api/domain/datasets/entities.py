from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from incrementality_api.domain.datasets.errors import (
    InvalidDatasetTransitionError,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)
from incrementality_api.domain.datasets.validation import (
    normalize_dataset_checksum,
    normalize_dataset_filename,
    normalize_dataset_media_type,
    normalize_dataset_storage_key,
    validate_dataset_byte_size,
)


@dataclass(frozen=True, slots=True)
class Dataset:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    created_by_user_id: UUID
    source_filename: str
    storage_key: str
    media_type: str
    byte_size: int
    checksum_sha256: str
    status: DatasetStatus
    created_at: datetime
    uploaded_at: datetime | None
    validation_completed_at: datetime | None
    row_count: int | None
    column_count: int | None
    failure_reason: str | None

    @classmethod
    def register(
        cls,
        *,
        workspace_id: UUID,
        project_id: UUID,
        created_by_user_id: UUID,
        source_filename: str,
        storage_key: str,
        media_type: str,
        byte_size: int,
        checksum_sha256: str,
    ) -> Self:
        return cls(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            created_by_user_id=created_by_user_id,
            source_filename=normalize_dataset_filename(
                source_filename,
            ),
            storage_key=normalize_dataset_storage_key(
                storage_key,
            ),
            media_type=normalize_dataset_media_type(
                media_type,
            ),
            byte_size=validate_dataset_byte_size(
                byte_size,
            ),
            checksum_sha256=normalize_dataset_checksum(
                checksum_sha256,
            ),
            status=DatasetStatus.PENDING_UPLOAD,
            created_at=datetime.now(UTC),
            uploaded_at=None,
            validation_completed_at=None,
            row_count=None,
            column_count=None,
            failure_reason=None,
        )

    def mark_uploaded(
        self,
        *,
        uploaded_at: datetime,
    ) -> Self:
        if self.status is not DatasetStatus.PENDING_UPLOAD:
            raise InvalidDatasetTransitionError(
                f"Dataset in status '{self.status.value}' cannot be marked uploaded."
            )

        if uploaded_at.tzinfo is None or uploaded_at.utcoffset() is None:
            raise InvalidDatasetTransitionError("Upload timestamp must be timezone-aware.")

        return replace(
            self,
            status=DatasetStatus.UPLOADED,
            uploaded_at=uploaded_at,
        )
