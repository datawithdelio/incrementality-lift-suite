from dataclasses import dataclass, replace
from datetime import datetime
from typing import Self
from uuid import UUID, uuid4

from incrementality_api.domain.analysis_runs.execution_job_errors import (
    InvalidAnalysisExecutionJobError,
    InvalidAnalysisExecutionJobTransitionError,
)
from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)

_MAX_ERROR_LENGTH = 2_000


@dataclass(frozen=True, slots=True)
class AnalysisExecutionJob:
    """Represent durable worker execution for one analysis run."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    analysis_run_id: UUID
    status: AnalysisExecutionJobStatus
    attempt_count: int
    max_attempts: int
    available_at: datetime
    claimed_at: datetime | None
    completed_at: datetime | None
    last_error: str | None
    created_at: datetime

    @classmethod
    def enqueue(
        cls,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
        created_at: datetime,
        available_at: datetime,
        max_attempts: int = 3,
    ) -> Self:
        cls._validate_creation_timestamp(
            created_at,
        )
        cls._validate_creation_timestamp(
            available_at,
        )

        if available_at < created_at:
            raise InvalidAnalysisExecutionJobError(
                "Analysis execution availability cannot precede creation."
            )

        if max_attempts <= 0:
            raise InvalidAnalysisExecutionJobError("Maximum attempts must be positive.")

        return cls(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            analysis_run_id=analysis_run_id,
            status=AnalysisExecutionJobStatus.PENDING,
            attempt_count=0,
            max_attempts=max_attempts,
            available_at=available_at,
            claimed_at=None,
            completed_at=None,
            last_error=None,
            created_at=created_at,
        )

    def claim(
        self,
        *,
        claimed_at: datetime,
    ) -> Self:
        self._validate_transition_timestamp(
            claimed_at,
        )

        if self.status is not AnalysisExecutionJobStatus.PENDING:
            raise InvalidAnalysisExecutionJobTransitionError(
                f"Analysis execution job in status '{self.status.value}' cannot be claimed."
            )

        if claimed_at < self.available_at:
            raise InvalidAnalysisExecutionJobTransitionError(
                "Analysis execution job is not available for claiming."
            )

        if self.attempt_count >= self.max_attempts:
            raise InvalidAnalysisExecutionJobTransitionError(
                "Analysis execution job has exhausted its attempts."
            )

        return replace(
            self,
            status=AnalysisExecutionJobStatus.RUNNING,
            attempt_count=self.attempt_count + 1,
            claimed_at=claimed_at,
            completed_at=None,
            last_error=None,
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
            status=AnalysisExecutionJobStatus.SUCCEEDED,
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
            raise InvalidAnalysisExecutionJobTransitionError(
                "Analysis execution job has exhausted its attempts."
            )

        if available_at < failed_at:
            raise InvalidAnalysisExecutionJobTransitionError(
                "Analysis execution retry availability cannot precede failure."
            )

        normalized_error = self._normalize_error(
            error,
        )

        return replace(
            self,
            status=AnalysisExecutionJobStatus.PENDING,
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

        normalized_error = self._normalize_error(
            error,
        )

        return replace(
            self,
            status=AnalysisExecutionJobStatus.DEAD_LETTER,
            completed_at=completed_at,
            last_error=normalized_error,
        )

    def _require_running(
        self,
        *,
        action: str,
    ) -> None:
        if self.status is not AnalysisExecutionJobStatus.RUNNING:
            raise InvalidAnalysisExecutionJobTransitionError(
                f"Analysis execution job in status '{self.status.value}' cannot be {action}."
            )

    def _validate_completion_timestamp(
        self,
        completed_at: datetime,
    ) -> None:
        self._validate_transition_timestamp(
            completed_at,
        )

        if self.claimed_at is None:
            raise InvalidAnalysisExecutionJobTransitionError(
                "Running analysis execution claim timestamp is missing."
            )

        if completed_at < self.claimed_at:
            raise InvalidAnalysisExecutionJobTransitionError(
                "Analysis execution completion timestamp cannot precede its claim timestamp."
            )

    @staticmethod
    def _normalize_error(
        error: str,
    ) -> str:
        normalized = error.strip()

        if not normalized:
            raise InvalidAnalysisExecutionJobTransitionError(
                "Analysis execution job error must not be blank."
            )

        if len(normalized) > _MAX_ERROR_LENGTH:
            raise InvalidAnalysisExecutionJobTransitionError(
                f"Analysis execution job error must not exceed {_MAX_ERROR_LENGTH} characters."
            )

        return normalized

    @staticmethod
    def _validate_creation_timestamp(
        timestamp: datetime,
    ) -> None:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidAnalysisExecutionJobError(
                "Analysis execution job timestamps must be timezone-aware."
            )

    @staticmethod
    def _validate_transition_timestamp(
        timestamp: datetime,
    ) -> None:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidAnalysisExecutionJobTransitionError(
                "Analysis execution job timestamps must be timezone-aware."
            )
