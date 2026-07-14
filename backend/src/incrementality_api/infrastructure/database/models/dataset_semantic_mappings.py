from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
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


class DatasetSemanticMappingModel(
    TimestampMixin,
    Base,
):
    """Persist one versioned causal-role mapping."""

    __tablename__ = "dataset_semantic_mappings"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "dataset_id",
            "version",
            name=("uq_dataset_semantic_mappings_id_dataset_version"),
        ),
        UniqueConstraint(
            "dataset_id",
            "version",
            name=("uq_dataset_semantic_mappings_dataset_version"),
        ),
        UniqueConstraint(
            "id",
            "dataset_id",
            name=("uq_dataset_semantic_mappings_id_dataset"),
        ),
        CheckConstraint(
            "version > 0",
            name=("ck_dataset_semantic_mappings_version_positive"),
        ),
        CheckConstraint(
            "btrim(time_column) <> ''",
            name=("ck_dataset_semantic_mappings_time_not_blank"),
        ),
        CheckConstraint(
            "btrim(unit_column) <> ''",
            name=("ck_dataset_semantic_mappings_unit_not_blank"),
        ),
        CheckConstraint(
            "btrim(treatment_column) <> ''",
            name=("ck_dataset_semantic_mappings_treatment_not_blank"),
        ),
        CheckConstraint(
            "btrim(outcome_column) <> ''",
            name=("ck_dataset_semantic_mappings_outcome_not_blank"),
        ),
        CheckConstraint(
            ("spend_column IS NULL OR btrim(spend_column) <> ''"),
            name=("ck_dataset_semantic_mappings_spend_not_blank"),
        ),
        CheckConstraint(
            "btrim(treatment_value) <> ''",
            name=("ck_dataset_semantic_mappings_treatment_value_not_blank"),
        ),
        CheckConstraint(
            "btrim(control_value) <> ''",
            name=("ck_dataset_semantic_mappings_control_value_not_blank"),
        ),
        CheckConstraint(
            """
            time_column <> unit_column
            AND time_column <> treatment_column
            AND time_column <> outcome_column
            AND unit_column <> treatment_column
            AND unit_column <> outcome_column
            AND treatment_column <> outcome_column
            AND
            (
                spend_column IS NULL
                OR
                (
                    spend_column <> time_column
                    AND spend_column <> unit_column
                    AND spend_column <> treatment_column
                    AND spend_column <> outcome_column
                )
            )
            """,
            name=("ck_dataset_semantic_mappings_roles_distinct"),
        ),
        CheckConstraint(
            ("lower(btrim(treatment_value)) <> lower(btrim(control_value))"),
            name=("ck_dataset_semantic_mappings_values_distinct"),
        ),
        ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=("fk_dataset_semantic_mappings_dataset"),
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=("fk_dataset_semantic_mappings_creator"),
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            [
                "dataset_id",
                "time_column",
            ],
            [
                "dataset_columns.dataset_id",
                "dataset_columns.normalized_name",
            ],
            name=("fk_dataset_semantic_mappings_time_column"),
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            [
                "dataset_id",
                "unit_column",
            ],
            [
                "dataset_columns.dataset_id",
                "dataset_columns.normalized_name",
            ],
            name=("fk_dataset_semantic_mappings_unit_column"),
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            [
                "dataset_id",
                "treatment_column",
            ],
            [
                "dataset_columns.dataset_id",
                "dataset_columns.normalized_name",
            ],
            name=("fk_dataset_semantic_mappings_treatment_column"),
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            [
                "dataset_id",
                "outcome_column",
            ],
            [
                "dataset_columns.dataset_id",
                "dataset_columns.normalized_name",
            ],
            name=("fk_dataset_semantic_mappings_outcome_column"),
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            [
                "dataset_id",
                "spend_column",
            ],
            [
                "dataset_columns.dataset_id",
                "dataset_columns.normalized_name",
            ],
            name=("fk_dataset_semantic_mappings_spend_column"),
            deferrable=True,
            initially="DEFERRED",
        ),
        Index(
            "ix_dataset_semantic_mappings_dataset_id",
            "dataset_id",
        ),
        Index(
            ("ix_dataset_semantic_mappings_created_by_user_id"),
            "created_by_user_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    time_column: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    unit_column: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    treatment_column: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    outcome_column: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    spend_column: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    treatment_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    control_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


class DatasetMappingCovariateModel(
    TimestampMixin,
    Base,
):
    """Persist one ordered semantic-mapping covariate."""

    __tablename__ = "dataset_mapping_covariates"
    __table_args__ = (
        UniqueConstraint(
            "mapping_id",
            "ordinal_position",
            name=("uq_dataset_mapping_covariates_mapping_ordinal"),
        ),
        UniqueConstraint(
            "mapping_id",
            "normalized_column_name",
            name=("uq_dataset_mapping_covariates_mapping_column"),
        ),
        CheckConstraint(
            "ordinal_position > 0",
            name=("ck_dataset_mapping_covariates_ordinal_positive"),
        ),
        CheckConstraint(
            "btrim(normalized_column_name) <> ''",
            name=("ck_dataset_mapping_covariates_column_not_blank"),
        ),
        ForeignKeyConstraint(
            [
                "mapping_id",
                "dataset_id",
            ],
            [
                "dataset_semantic_mappings.id",
                "dataset_semantic_mappings.dataset_id",
            ],
            name=("fk_dataset_mapping_covariates_mapping"),
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            [
                "dataset_id",
                "normalized_column_name",
            ],
            [
                "dataset_columns.dataset_id",
                "dataset_columns.normalized_name",
            ],
            name=("fk_dataset_mapping_covariates_column"),
            deferrable=True,
            initially="DEFERRED",
        ),
        Index(
            "ix_dataset_mapping_covariates_mapping_id",
            "mapping_id",
        ),
        Index(
            ("ix_dataset_mapping_covariates_dataset_column"),
            "dataset_id",
            "normalized_column_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    mapping_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    ordinal_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    normalized_column_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
