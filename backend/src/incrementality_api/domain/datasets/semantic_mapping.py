from dataclasses import dataclass
from datetime import datetime
from typing import Self
from uuid import UUID, uuid4

from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetSemanticMappingError,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

_NUMERIC_TYPES = {
    DatasetColumnType.INTEGER,
    DatasetColumnType.FLOAT,
}

_TIME_TYPES = {
    DatasetColumnType.DATE,
    DatasetColumnType.DATETIME,
}

_UNIT_TYPES = {
    DatasetColumnType.INTEGER,
    DatasetColumnType.STRING,
}

_TREATMENT_TYPES = {
    DatasetColumnType.BOOLEAN,
    DatasetColumnType.INTEGER,
    DatasetColumnType.STRING,
}

_MAX_VALUE_LENGTH = 255


@dataclass(frozen=True, slots=True)
class DatasetSemanticMapping:
    """Assign validated causal roles to dataset columns."""

    id: UUID
    dataset_id: UUID
    created_by_user_id: UUID
    version: int
    time_column: str
    unit_column: str
    treatment_column: str | None
    outcome_column: str
    spend_column: str | None
    covariate_columns: tuple[str, ...]
    treatment_value: str | None
    control_value: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        dataset: Dataset,
        columns: tuple[
            DatasetColumnProfile,
            ...,
        ],
        created_by_user_id: UUID,
        version: int,
        time_column: str,
        unit_column: str,
        treatment_column: str | None,
        outcome_column: str,
        spend_column: str | None,
        covariate_columns: tuple[str, ...],
        treatment_value: str | None,
        control_value: str | None,
        created_at: datetime,
    ) -> Self:
        if dataset.status is not DatasetStatus.READY:
            raise InvalidDatasetSemanticMappingError(
                "Dataset must be ready before semantic mapping."
            )

        if version <= 0:
            raise InvalidDatasetSemanticMappingError("Semantic mapping version must be positive.")

        cls._validate_aware_timestamp(
            created_at,
        )

        columns_by_name = {column.normalized_name: column for column in columns}

        if len(columns_by_name) != len(columns):
            raise InvalidDatasetSemanticMappingError(
                "Dataset columns must have unique normalized names."
            )

        normalized_time = cls._normalize_column_name(
            time_column,
        )
        normalized_unit = cls._normalize_column_name(
            unit_column,
        )
        treatment_fields = (
            treatment_column,
            treatment_value,
            control_value,
        )

        if any(value is None for value in treatment_fields) and not all(
            value is None for value in treatment_fields
        ):
            raise InvalidDatasetSemanticMappingError(
                "Treatment column, treatment value, and control value must be supplied together."
            )

        normalized_treatment = (
            None
            if treatment_column is None
            else cls._normalize_column_name(treatment_column)
        )
        normalized_outcome = cls._normalize_column_name(
            outcome_column,
        )
        normalized_spend = (
            None
            if spend_column is None
            else cls._normalize_column_name(
                spend_column,
            )
        )

        normalized_covariates = tuple(
            cls._normalize_column_name(name) for name in covariate_columns
        )

        assigned_roles = [
            normalized_time,
            normalized_unit,
            normalized_outcome,
        ]

        if normalized_treatment is not None:
            assigned_roles.append(normalized_treatment)

        if normalized_spend is not None:
            assigned_roles.append(
                normalized_spend,
            )

        if len(set(assigned_roles)) != len(assigned_roles):
            raise InvalidDatasetSemanticMappingError("Semantic roles must use distinct columns.")

        if len(set(normalized_covariates)) != len(normalized_covariates):
            raise InvalidDatasetSemanticMappingError("Covariate columns must be unique.")

        if set(normalized_covariates).intersection(assigned_roles):
            raise InvalidDatasetSemanticMappingError(
                "Covariate columns must not overlap assigned semantic roles."
            )

        time_profile = cls._require_column(
            columns_by_name,
            normalized_time,
        )
        unit_profile = cls._require_column(
            columns_by_name,
            normalized_unit,
        )
        treatment_profile = (
            None
            if normalized_treatment is None
            else cls._require_column(
                columns_by_name,
                normalized_treatment,
            )
        )
        outcome_profile = cls._require_column(
            columns_by_name,
            normalized_outcome,
        )

        for covariate in normalized_covariates:
            cls._require_column(
                columns_by_name,
                covariate,
            )

        if time_profile.inferred_type not in _TIME_TYPES:
            raise InvalidDatasetSemanticMappingError("Time column must be date or datetime.")

        if unit_profile.inferred_type not in _UNIT_TYPES:
            raise InvalidDatasetSemanticMappingError("Unit column must be string or integer.")

        if (
            treatment_profile is not None
            and treatment_profile.inferred_type not in _TREATMENT_TYPES
        ):
            raise InvalidDatasetSemanticMappingError(
                "Treatment column must be boolean, integer, or string."
            )

        if outcome_profile.inferred_type not in _NUMERIC_TYPES:
            raise InvalidDatasetSemanticMappingError("Outcome column must be numeric.")

        if normalized_spend is not None:
            spend_profile = cls._require_column(
                columns_by_name,
                normalized_spend,
            )

            if spend_profile.inferred_type not in _NUMERIC_TYPES:
                raise InvalidDatasetSemanticMappingError("Spend column must be numeric.")

        normalized_treatment_value = (
            None
            if treatment_value is None
            else cls._normalize_value(
                treatment_value,
                field_name="Treatment value",
            )
        )
        normalized_control_value = (
            None
            if control_value is None
            else cls._normalize_value(
                control_value,
                field_name="Control value",
            )
        )

        if (
            normalized_treatment_value is not None
            and normalized_control_value is not None
            and normalized_treatment_value.casefold() == normalized_control_value.casefold()
        ):
            raise InvalidDatasetSemanticMappingError(
                "Treatment and control values must be distinct."
            )

        return cls(
            id=uuid4(),
            dataset_id=dataset.id,
            created_by_user_id=created_by_user_id,
            version=version,
            time_column=normalized_time,
            unit_column=normalized_unit,
            treatment_column=normalized_treatment,
            outcome_column=normalized_outcome,
            spend_column=normalized_spend,
            covariate_columns=normalized_covariates,
            treatment_value=normalized_treatment_value,
            control_value=normalized_control_value,
            created_at=created_at,
            updated_at=created_at,
        )

    @staticmethod
    def _normalize_column_name(
        value: str,
    ) -> str:
        normalized = value.strip().casefold()

        if not normalized:
            raise InvalidDatasetSemanticMappingError("Mapped column name must not be blank.")

        if len(normalized) > 255:
            raise InvalidDatasetSemanticMappingError(
                "Mapped column name must not exceed 255 characters."
            )

        return normalized

    @staticmethod
    def _normalize_value(
        value: str,
        *,
        field_name: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise InvalidDatasetSemanticMappingError(f"{field_name} must not be blank.")

        if len(normalized) > _MAX_VALUE_LENGTH:
            raise InvalidDatasetSemanticMappingError(
                f"{field_name} must not exceed {_MAX_VALUE_LENGTH} characters."
            )

        return normalized

    @staticmethod
    def _require_column(
        columns_by_name: dict[
            str,
            DatasetColumnProfile,
        ],
        normalized_name: str,
    ) -> DatasetColumnProfile:
        column = columns_by_name.get(
            normalized_name,
        )

        if column is None:
            raise InvalidDatasetSemanticMappingError(
                f"Mapped column '{normalized_name}' does not exist."
            )

        return column

    @staticmethod
    def _validate_aware_timestamp(
        timestamp: datetime,
    ) -> None:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidDatasetSemanticMappingError(
                "Semantic mapping timestamp must be timezone-aware."
            )
