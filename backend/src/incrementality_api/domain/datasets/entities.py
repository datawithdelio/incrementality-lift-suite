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
    validation_started_at: datetime | None = None

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
            validation_started_at=None,
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

        self._validate_aware_timestamp(
            uploaded_at,
            message=("Upload timestamp must be timezone-aware."),
        )

        return replace(
            self,
            status=DatasetStatus.UPLOADED,
            uploaded_at=uploaded_at,
        )

    def begin_validation(
        self,
        *,
        validation_started_at: datetime,
    ) -> Self:
        if self.status is not DatasetStatus.UPLOADED:
            raise InvalidDatasetTransitionError(
                f"Dataset in status '{self.status.value}' cannot begin validation."
            )

        self._validate_aware_timestamp(
            validation_started_at,
            message=("Validation start timestamp must be timezone-aware."),
        )

        return replace(
            self,
            status=DatasetStatus.VALIDATING,
            validation_started_at=validation_started_at,
            validation_completed_at=None,
            row_count=None,
            column_count=None,
            failure_reason=None,
        )

    def mark_ready(
        self,
        *,
        validation_completed_at: datetime,
        row_count: int,
        column_count: int,
    ) -> Self:
        if self.status is not DatasetStatus.VALIDATING:
            raise InvalidDatasetTransitionError(
                f"Dataset in status '{self.status.value}' cannot be marked ready."
            )

        self._validate_completion_timestamp(
            validation_completed_at,
        )

        if row_count < 0:
            raise InvalidDatasetTransitionError("Row count must be nonnegative.")

        if column_count <= 0:
            raise InvalidDatasetTransitionError("Column count must be positive.")

        return replace(
            self,
            status=DatasetStatus.READY,
            validation_completed_at=(validation_completed_at),
            row_count=row_count,
            column_count=column_count,
            failure_reason=None,
        )

    def mark_failed(
        self,
        *,
        validation_completed_at: datetime,
        failure_reason: str,
    ) -> Self:
        if self.status is not DatasetStatus.VALIDATING:
            raise InvalidDatasetTransitionError(
                f"Dataset in status '{self.status.value}' cannot be marked failed."
            )

        self._validate_completion_timestamp(
            validation_completed_at,
        )

        normalized_reason = failure_reason.strip()

        if not normalized_reason:
            raise InvalidDatasetTransitionError("Failure reason must not be blank.")

        if len(normalized_reason) > 2_000:
            raise InvalidDatasetTransitionError("Failure reason must not exceed 2000 characters.")

        return replace(
            self,
            status=DatasetStatus.FAILED,
            validation_completed_at=(validation_completed_at),
            row_count=None,
            column_count=None,
            failure_reason=normalized_reason,
        )

    def _validate_completion_timestamp(
        self,
        validation_completed_at: datetime,
    ) -> None:
        self._validate_aware_timestamp(
            validation_completed_at,
            message=("Validation completion timestamp must be timezone-aware."),
        )

        if self.validation_started_at is None:
            raise InvalidDatasetTransitionError("Validation start timestamp is missing.")

        if validation_completed_at < self.validation_started_at:
            raise InvalidDatasetTransitionError(
                "Validation completion timestamp cannot precede the validation start timestamp."
            )

    @staticmethod
    def _validate_aware_timestamp(
        timestamp: datetime,
        *,
        message: str,
    ) -> None:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidDatasetTransitionError(message)
