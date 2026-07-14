from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
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


class DatasetColumnModel(TimestampMixin, Base):
    """Persist the discovered schema of one dataset."""

    __tablename__ = "dataset_columns"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "ordinal_position",
            name=("uq_dataset_columns_dataset_ordinal"),
        ),
        UniqueConstraint(
            "dataset_id",
            "normalized_name",
            name=("uq_dataset_columns_dataset_normalized_name"),
        ),
        CheckConstraint(
            "ordinal_position > 0",
            name=("ck_dataset_columns_ordinal_positive"),
        ),
        CheckConstraint(
            "btrim(source_name) <> ''",
            name=("ck_dataset_columns_source_name_not_blank"),
        ),
        CheckConstraint(
            "btrim(normalized_name) <> ''",
            name=("ck_dataset_columns_normalized_name_not_blank"),
        ),
        CheckConstraint(
            ("inferred_type IN ('boolean', 'integer', 'float', 'date', 'datetime', 'string')"),
            name=("ck_dataset_columns_inferred_type"),
        ),
        CheckConstraint(
            "missing_count >= 0",
            name=("ck_dataset_columns_missing_nonnegative"),
        ),
        CheckConstraint(
            "nullable = (missing_count > 0)",
            name=("ck_dataset_columns_nullable_consistency"),
        ),
        Index(
            "ix_dataset_columns_dataset_id",
            "dataset_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "datasets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    ordinal_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    source_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    inferred_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    nullable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    missing_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
