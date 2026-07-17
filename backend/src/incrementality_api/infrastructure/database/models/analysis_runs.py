from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from incrementality_api.infrastructure.database.base import (
    Base,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    TimestampMixin,
)


class AnalysisRunModel(
    TimestampMixin,
    Base,
):
    """Persist one reproducible causal-analysis run."""

    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "workspace_id",
            "project_id",
            name="uq_analysis_runs_id_workspace_project",
        ),
        CheckConstraint(
            "semantic_mapping_version > 0",
            name=("ck_analysis_runs_mapping_version_positive"),
        ),
        CheckConstraint(
            "dataset_checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_analysis_runs_dataset_checksum_sha256_format",
        ),
        CheckConstraint(
            ("input_fingerprint_sha256 IS NULL OR input_fingerprint_sha256 ~ '^[0-9a-f]{64}$'"),
            name=("ck_analysis_runs_input_fingerprint_sha256_format"),
        ),
        CheckConstraint(
            "dataset_byte_size > 0",
            name="ck_analysis_runs_dataset_byte_size_positive",
        ),
        CheckConstraint(
            """
            estimator_type IN (
                'difference_in_differences',
                'synthetic_control',
                'geo_holdout',
                'marketing_mix_model',
                'off_policy_evaluation'
            )
            """,
            name="ck_analysis_runs_estimator_type",
        ),
        CheckConstraint(
            "btrim(estimator_version) <> ''",
            name=("ck_analysis_runs_estimator_version_not_blank"),
        ),
        CheckConstraint(
            ("application_version IS NULL OR btrim(application_version) <> ''"),
            name=("ck_analysis_runs_application_version_not_blank"),
        ),
        CheckConstraint(
            ("source_revision IS NULL OR btrim(source_revision) <> ''"),
            name=("ck_analysis_runs_source_revision_not_blank"),
        ),
        CheckConstraint(
            (
                "statistical_library_versions_json IS NULL "
                "OR btrim(statistical_library_versions_json) <> ''"
            ),
            name=("ck_analysis_runs_statistical_library_versions_not_blank"),
        ),
        CheckConstraint(
            (
                "statistical_library_versions_json IS NULL "
                "OR jsonb_typeof(statistical_library_versions_json::jsonb) = 'object'"
            ),
            name=("ck_analysis_runs_statistical_library_versions_object"),
        ),
        CheckConstraint(
            (
                "statistical_library_versions_json IS NULL "
                "OR statistical_library_versions_json::jsonb <> '{}'::jsonb"
            ),
            name=("ck_analysis_runs_statistical_library_versions_not_empty"),
        ),
        CheckConstraint(
            "btrim(configuration_json) <> ''",
            name=("ck_analysis_runs_configuration_not_blank"),
        ),
        CheckConstraint(
            ("jsonb_typeof(configuration_json::jsonb) = 'object'"),
            name=("ck_analysis_runs_configuration_object"),
        ),
        CheckConstraint(
            """
            status IN (
                'queued',
                'running',
                'succeeded',
                'failed',
                'cancelled'
            )
            """,
            name="ck_analysis_runs_status",
        ),
        CheckConstraint(
            ("failure_reason IS NULL OR btrim(failure_reason) <> ''"),
            name=("ck_analysis_runs_failure_reason_not_blank"),
        ),
        CheckConstraint(
            ("cancellation_reason IS NULL OR btrim(cancellation_reason) <> ''"),
            name=("ck_analysis_runs_cancellation_reason_not_blank"),
        ),
        CheckConstraint(
            ("started_at IS NULL OR started_at >= created_at"),
            name=("ck_analysis_runs_start_after_create"),
        ),
        CheckConstraint(
            ("completed_at IS NULL OR completed_at >= created_at"),
            name=("ck_analysis_runs_completion_after_create"),
        ),
        CheckConstraint(
            """
            completed_at IS NULL
            OR started_at IS NULL
            OR completed_at >= started_at
            """,
            name=("ck_analysis_runs_completion_after_start"),
        ),
        CheckConstraint(
            """
            (
                status = 'queued'
                AND started_at IS NULL
                AND completed_at IS NULL
                AND failure_reason IS NULL
                AND cancellation_reason IS NULL
            )
            OR
            (
                status = 'running'
                AND started_at IS NOT NULL
                AND completed_at IS NULL
                AND failure_reason IS NULL
                AND cancellation_reason IS NULL
            )
            OR
            (
                status = 'succeeded'
                AND started_at IS NOT NULL
                AND completed_at IS NOT NULL
                AND failure_reason IS NULL
                AND cancellation_reason IS NULL
            )
            OR
            (
                status = 'failed'
                AND started_at IS NOT NULL
                AND completed_at IS NOT NULL
                AND failure_reason IS NOT NULL
                AND cancellation_reason IS NULL
            )
            OR
            (
                status = 'cancelled'
                AND completed_at IS NOT NULL
                AND failure_reason IS NULL
                AND cancellation_reason IS NOT NULL
            )
            """,
            name=("ck_analysis_runs_lifecycle_metadata"),
        ),
        ForeignKeyConstraint(
            [
                "dataset_id",
                "workspace_id",
                "project_id",
            ],
            [
                "datasets.id",
                "datasets.workspace_id",
                "datasets.project_id",
            ],
            name="fk_analysis_runs_dataset_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            [
                "semantic_mapping_id",
                "dataset_id",
                "semantic_mapping_version",
            ],
            [
                "dataset_semantic_mappings.id",
                "dataset_semantic_mappings.dataset_id",
                "dataset_semantic_mappings.version",
            ],
            name=("fk_analysis_runs_semantic_mapping_snapshot"),
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_analysis_runs_creator",
            ondelete="RESTRICT",
        ),
        Index(
            ("ix_analysis_runs_workspace_project_created_at"),
            "workspace_id",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_analysis_runs_dataset_created_at",
            "dataset_id",
            "created_at",
        ),
        Index(
            "ix_analysis_runs_status_created_at",
            "status",
            "created_at",
        ),
        Index(
            "ix_analysis_runs_semantic_mapping_id",
            "semantic_mapping_id",
        ),
        Index(
            "ix_analysis_runs_created_by_user_id",
            "created_by_user_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    dataset_checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    dataset_byte_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    semantic_mapping_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    semantic_mapping_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    estimator_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    estimator_version: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    application_version: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    source_revision: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    statistical_library_versions_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    random_seed: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    input_fingerprint_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    configuration_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(2_000),
        nullable=True,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        String(2_000),
        nullable=True,
    )
