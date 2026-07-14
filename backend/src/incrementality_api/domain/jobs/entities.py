from dataclasses import dataclass, replace
from datetime import datetime
from typing import Self
from uuid import UUID, uuid4

from incrementality_api.domain.jobs.errors import (
    InvalidJobError,
    InvalidJobTransitionError,
)
from incrementality_api.domain.jobs.status import (
    DatasetValidationJobStatus,
)


@dataclass(frozen=True, slots=True)
class DatasetValidationJob:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    status: DatasetValidationJobStatus
    attempt_count: int
    max_attempts: int
    available_at: datetime
    created_at: datetime
    claimed_at: datetime | None
    completed_at: datetime | None
    last_error: str | None

    @classmethod
    def enqueue(
        cls,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        created_at: datetime,
        available_at: datetime,
        max_attempts: int = 3,
    ) -> Self:
        cls._validate_enqueue_timestamp(created_at)
        cls._validate_enqueue_timestamp(available_at)

        if max_attempts <= 0:
            raise InvalidJobError("Maximum attempts must be positive.")

        if available_at < created_at:
            raise InvalidJobError(
                "Job availability timestamp cannot precede its creation timestamp."
            )

        return cls(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
            status=DatasetValidationJobStatus.PENDING,
            attempt_count=0,
            max_attempts=max_attempts,
            available_at=available_at,
            created_at=created_at,
            claimed_at=None,
            completed_at=None,
            last_error=None,
        )

    def claim(
        self,
        *,
        claimed_at: datetime,
    ) -> Self:
        if self.status is not DatasetValidationJobStatus.PENDING:
            raise InvalidJobTransitionError(
                f"Job in status '{self.status.value}' cannot be claimed."
            )

        self._validate_transition_timestamp(claimed_at)

        if claimed_at < self.available_at:
            raise InvalidJobTransitionError("Job is not available for claiming.")

        if self.attempt_count >= self.max_attempts:
            raise InvalidJobTransitionError("Job has exhausted its attempts.")

        return replace(
            self,
            status=DatasetValidationJobStatus.RUNNING,
            attempt_count=self.attempt_count + 1,
            claimed_at=claimed_at,
            completed_at=None,
        )

    def mark_succeeded(
        self,
        *,
        completed_at: datetime,
    ) -> Self:
        self._require_running(
            action="marked succeeded",
        )
        self._validate_completion_timestamp(
            completed_at,
        )

        return replace(
            self,
            status=DatasetValidationJobStatus.SUCCEEDED,
            completed_at=completed_at,
            last_error=None,
        )

    def retry(
        self,
        *,
        failed_at: datetime,
        available_at: datetime,
        error: str,
    ) -> Self:
        self._require_running(
            action="retried",
        )
        self._validate_completion_timestamp(
            failed_at,
        )
        self._validate_transition_timestamp(
            available_at,
        )

        if self.attempt_count >= self.max_attempts:
            raise InvalidJobTransitionError("Job has exhausted its attempts.")

        if available_at < failed_at:
            raise InvalidJobTransitionError(
                "Retry availability timestamp cannot precede the failure timestamp."
            )

        normalized_error = self._normalize_error(error)

        return replace(
            self,
            status=DatasetValidationJobStatus.PENDING,
            available_at=available_at,
            claimed_at=None,
            completed_at=None,
            last_error=normalized_error,
        )

    def mark_dead_letter(
        self,
        *,
        completed_at: datetime,
        error: str,
    ) -> Self:
        self._require_running(
            action="marked dead letter",
        )
        self._validate_completion_timestamp(
            completed_at,
        )

        normalized_error = self._normalize_error(error)

        return replace(
            self,
            status=DatasetValidationJobStatus.DEAD_LETTER,
            completed_at=completed_at,
            last_error=normalized_error,
        )

    def _require_running(
        self,
        *,
        action: str,
    ) -> None:
        if self.status is not DatasetValidationJobStatus.RUNNING:
            raise InvalidJobTransitionError(
                f"Job in status '{self.status.value}' cannot be {action}."
            )

    def _validate_completion_timestamp(
        self,
        completed_at: datetime,
    ) -> None:
        self._validate_transition_timestamp(
            completed_at,
        )

        if self.claimed_at is None:
            raise InvalidJobTransitionError("Running job claim timestamp is missing.")

        if completed_at < self.claimed_at:
            raise InvalidJobTransitionError(
                "Job completion timestamp cannot precede its claim timestamp."
            )

    @staticmethod
    def _normalize_error(
        error: str,
    ) -> str:
        normalized_error = error.strip()

        if not normalized_error:
            raise InvalidJobTransitionError("Job error must not be blank.")

        if len(normalized_error) > 2_000:
            raise InvalidJobTransitionError("Job error must not exceed 2000 characters.")

        return normalized_error

    @staticmethod
    def _validate_enqueue_timestamp(
        timestamp: datetime,
    ) -> None:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidJobError("Job timestamps must be timezone-aware.")

    @staticmethod
    def _validate_transition_timestamp(
        timestamp: datetime,
    ) -> None:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidJobTransitionError("Job timestamps must be timezone-aware.")
