import json
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
from typing import Any, Self
from uuid import UUID, uuid4

from incrementality_api.domain.analysis_runs.errors import (
    InvalidAnalysisRunError,
    InvalidAnalysisRunTransitionError,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)

_MAX_ESTIMATOR_VERSION_LENGTH = 255
_MAX_REASON_LENGTH = 2_000


@dataclass(frozen=True, slots=True)
class AnalysisRun:
    """Represent one reproducible causal-analysis execution."""

    id: UUID
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    dataset_checksum_sha256: str
    dataset_byte_size: int
    semantic_mapping_id: UUID
    semantic_mapping_version: int
    created_by_user_id: UUID
    estimator_type: AnalysisEstimatorType
    estimator_version: str
    application_version: str | None
    source_revision: str | None
    random_seed: int | None
    input_fingerprint_sha256: str | None
    configuration_json: str
    status: AnalysisRunStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failure_reason: str | None
    cancellation_reason: str | None

    @classmethod
    def queue(
        cls,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        dataset_checksum_sha256: str,
        dataset_byte_size: int,
        semantic_mapping_id: UUID,
        semantic_mapping_version: int,
        created_by_user_id: UUID,
        estimator_type: AnalysisEstimatorType,
        estimator_version: str,
        application_version: str,
        source_revision: str,
        random_seed: int,
        configuration_json: str,
        created_at: datetime,
    ) -> Self:
        cls._validate_creation_timestamp(
            created_at,
        )

        if semantic_mapping_version <= 0:
            raise InvalidAnalysisRunError("Semantic mapping version must be positive.")

        normalized_estimator_version = cls._normalize_estimator_version(estimator_version)

        normalized_application_version = cls._normalize_runtime_version(
            application_version,
            field_name="Application version",
        )
        normalized_source_revision = cls._normalize_runtime_version(
            source_revision,
            field_name="Source revision",
        )
        canonical_configuration = cls._canonicalize_configuration(configuration_json)

        input_fingerprint_sha256 = cls._build_input_fingerprint_sha256(
            dataset_checksum_sha256=dataset_checksum_sha256,
            dataset_byte_size=dataset_byte_size,
            semantic_mapping_id=semantic_mapping_id,
            semantic_mapping_version=semantic_mapping_version,
            estimator_type=estimator_type,
            estimator_version=normalized_estimator_version,
            application_version=normalized_application_version,
            source_revision=normalized_source_revision,
            random_seed=random_seed,
            configuration_json=canonical_configuration,
        )

        return cls(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
            dataset_checksum_sha256=dataset_checksum_sha256,
            dataset_byte_size=dataset_byte_size,
            semantic_mapping_id=semantic_mapping_id,
            semantic_mapping_version=(semantic_mapping_version),
            created_by_user_id=created_by_user_id,
            estimator_type=estimator_type,
            estimator_version=(normalized_estimator_version),
            application_version=normalized_application_version,
            source_revision=normalized_source_revision,
            random_seed=random_seed,
            input_fingerprint_sha256=input_fingerprint_sha256,
            configuration_json=(canonical_configuration),
            status=AnalysisRunStatus.QUEUED,
            created_at=created_at,
            started_at=None,
            completed_at=None,
            failure_reason=None,
            cancellation_reason=None,
        )

    def start(
        self,
        *,
        started_at: datetime,
    ) -> Self:
        if self.status is not AnalysisRunStatus.QUEUED:
            raise InvalidAnalysisRunTransitionError(
                f"Analysis run in status '{self.status.value}' cannot be started."
            )

        self._validate_transition_timestamp(started_at)

        if started_at < self.created_at:
            raise InvalidAnalysisRunTransitionError(
                "Analysis start timestamp cannot precede creation."
            )

        return replace(
            self,
            status=AnalysisRunStatus.RUNNING,
            started_at=started_at,
            completed_at=None,
            failure_reason=None,
            cancellation_reason=None,
        )

    def mark_succeeded(
        self,
        *,
        completed_at: datetime,
    ) -> Self:
        self._require_running(
            action="marked succeeded",
        )
        self._validate_completion_timestamp(completed_at)

        return replace(
            self,
            status=AnalysisRunStatus.SUCCEEDED,
            completed_at=completed_at,
            failure_reason=None,
            cancellation_reason=None,
        )

    def mark_failed(
        self,
        *,
        completed_at: datetime,
        reason: str,
    ) -> Self:
        self._require_running(
            action="marked failed",
        )
        self._validate_completion_timestamp(completed_at)

        normalized_reason = self._normalize_reason(
            reason,
            field_name="Failure reason",
        )

        return replace(
            self,
            status=AnalysisRunStatus.FAILED,
            completed_at=completed_at,
            failure_reason=normalized_reason,
            cancellation_reason=None,
        )

    def cancel(
        self,
        *,
        cancelled_at: datetime,
        reason: str,
    ) -> Self:
        if self.status not in {
            AnalysisRunStatus.QUEUED,
            AnalysisRunStatus.RUNNING,
        }:
            raise InvalidAnalysisRunTransitionError(
                f"Analysis run in status '{self.status.value}' cannot be cancelled."
            )

        self._validate_transition_timestamp(cancelled_at)

        lower_bound = self.started_at if self.started_at is not None else self.created_at

        if cancelled_at < lower_bound:
            raise InvalidAnalysisRunTransitionError(
                "Analysis cancellation timestamp cannot precede its current lifecycle timestamp."
            )

        normalized_reason = self._normalize_reason(
            reason,
            field_name="Cancellation reason",
        )

        return replace(
            self,
            status=AnalysisRunStatus.CANCELLED,
            completed_at=cancelled_at,
            failure_reason=None,
            cancellation_reason=normalized_reason,
        )

    def _require_running(
        self,
        *,
        action: str,
    ) -> None:
        if self.status is not AnalysisRunStatus.RUNNING:
            raise InvalidAnalysisRunTransitionError(
                f"Analysis run in status '{self.status.value}' cannot be {action}."
            )

    def _validate_completion_timestamp(
        self,
        completed_at: datetime,
    ) -> None:
        self._validate_transition_timestamp(completed_at)

        if self.started_at is None:
            raise InvalidAnalysisRunTransitionError("Running analysis start timestamp is missing.")

        if completed_at < self.started_at:
            raise InvalidAnalysisRunTransitionError(
                "Analysis completion timestamp cannot precede its start timestamp."
            )

    @staticmethod
    def _normalize_runtime_version(
        value: str,
        *,
        field_name: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise InvalidAnalysisRunError(f"{field_name} must not be blank.")

        if len(normalized) > 255:
            raise InvalidAnalysisRunError(f"{field_name} must not exceed 255 characters.")

        return normalized

    @staticmethod
    def _build_input_fingerprint_sha256(
        *,
        dataset_checksum_sha256: str,
        dataset_byte_size: int,
        semantic_mapping_id: UUID,
        semantic_mapping_version: int,
        estimator_type: AnalysisEstimatorType,
        estimator_version: str,
        application_version: str,
        source_revision: str,
        random_seed: int,
        configuration_json: str,
    ) -> str:
        canonical_input = json.dumps(
            {
                "configuration_json": configuration_json,
                "dataset_byte_size": dataset_byte_size,
                "dataset_checksum_sha256": dataset_checksum_sha256,
                "estimator_type": estimator_type.value,
                "estimator_version": estimator_version,
                "application_version": application_version,
                "source_revision": source_revision,
                "random_seed": random_seed,
                "semantic_mapping_id": str(semantic_mapping_id),
                "semantic_mapping_version": semantic_mapping_version,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

        return sha256(
            canonical_input.encode("utf-8"),
        ).hexdigest()

    @staticmethod
    def _normalize_estimator_version(
        estimator_version: str,
    ) -> str:
        normalized = estimator_version.strip()

        if not normalized:
            raise InvalidAnalysisRunError("Estimator version must not be blank.")

        if len(normalized) > _MAX_ESTIMATOR_VERSION_LENGTH:
            raise InvalidAnalysisRunError(
                f"Estimator version must not exceed {_MAX_ESTIMATOR_VERSION_LENGTH} characters."
            )

        return normalized

    @staticmethod
    def _canonicalize_configuration(
        configuration_json: str,
    ) -> str:
        if not configuration_json.strip():
            raise InvalidAnalysisRunError("Analysis configuration must not be blank.")

        try:
            configuration: Any = json.loads(
                configuration_json,
                parse_constant=(AnalysisRun._reject_non_finite_constant),
            )
        except (
            json.JSONDecodeError,
            ValueError,
        ) as error:
            raise InvalidAnalysisRunError("Analysis configuration must be valid JSON.") from error

        if not isinstance(
            configuration,
            dict,
        ):
            raise InvalidAnalysisRunError("Analysis configuration must be a JSON object.")

        return json.dumps(
            configuration,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    @staticmethod
    def _reject_non_finite_constant(
        value: str,
    ) -> None:
        raise ValueError(f"Non-finite JSON constant is invalid: {value}")

    @staticmethod
    def _normalize_reason(
        reason: str,
        *,
        field_name: str,
    ) -> str:
        normalized = reason.strip()

        if not normalized:
            raise InvalidAnalysisRunTransitionError(f"{field_name} must not be blank.")

        if len(normalized) > _MAX_REASON_LENGTH:
            raise InvalidAnalysisRunTransitionError(
                f"{field_name} must not exceed {_MAX_REASON_LENGTH} characters."
            )

        return normalized

    @staticmethod
    def _validate_creation_timestamp(
        timestamp: datetime,
    ) -> None:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidAnalysisRunError("Analysis run timestamps must be timezone-aware.")

    @staticmethod
    def _validate_transition_timestamp(
        timestamp: datetime,
    ) -> None:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidAnalysisRunTransitionError(
                "Analysis run timestamps must be timezone-aware."
            )
