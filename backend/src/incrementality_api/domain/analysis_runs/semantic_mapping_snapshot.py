import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Self

from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError

_MAX_VALUE_LENGTH = 255
_SNAPSHOT_KEYS = {
    "time_column",
    "unit_column",
    "treatment_column",
    "outcome_column",
    "spend_column",
    "covariate_columns",
    "treatment_value",
    "control_value",
}


@dataclass(frozen=True, slots=True)
class SemanticMappingSnapshot:
    """Immutable, canonical semantic roles used by one analysis run."""

    time_column: str
    unit_column: str
    treatment_column: str
    outcome_column: str
    spend_column: str | None
    covariate_columns: tuple[str, ...]
    treatment_value: str
    control_value: str

    @classmethod
    def create(
        cls,
        *,
        time_column: str,
        unit_column: str,
        treatment_column: str,
        outcome_column: str,
        spend_column: str | None,
        covariate_columns: Sequence[str],
        treatment_value: str,
        control_value: str,
    ) -> Self:
        time = cls._normalize_column(time_column)
        unit = cls._normalize_column(unit_column)
        treatment = cls._normalize_column(treatment_column)
        outcome = cls._normalize_column(outcome_column)
        spend = None if spend_column is None else cls._normalize_column(spend_column)
        covariates = tuple(cls._normalize_column(name) for name in covariate_columns)
        treated = cls._normalize_value(treatment_value, field_name="Treatment value")
        control = cls._normalize_value(control_value, field_name="Control value")

        reserved = [time, unit, treatment, outcome]
        if spend is not None:
            reserved.append(spend)
        if len(set(reserved)) != len(reserved):
            raise InvalidAnalysisRunError("Semantic roles must use distinct columns.")
        if len(set(covariates)) != len(covariates):
            raise InvalidAnalysisRunError("Covariate columns must be unique.")
        if set(covariates).intersection(reserved):
            raise InvalidAnalysisRunError(
                "Covariate columns must not overlap assigned semantic roles."
            )
        if treated.casefold() == control.casefold():
            raise InvalidAnalysisRunError("Treatment and control values must be distinct.")

        return cls(
            time_column=time,
            unit_column=unit,
            treatment_column=treatment,
            outcome_column=outcome,
            spend_column=spend,
            covariate_columns=covariates,
            treatment_value=treated,
            control_value=control,
        )

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> Self:
        if set(values) != _SNAPSHOT_KEYS:
            raise InvalidAnalysisRunError("Semantic mapping snapshot has invalid fields.")
        covariates = values["covariate_columns"]
        string_fields = (
            "time_column",
            "unit_column",
            "treatment_column",
            "outcome_column",
            "treatment_value",
            "control_value",
        )
        if not all(isinstance(values[field], str) for field in string_fields):
            raise InvalidAnalysisRunError("Semantic mapping snapshot fields have invalid types.")
        spend = values["spend_column"]
        if spend is not None and not isinstance(spend, str):
            raise InvalidAnalysisRunError("Semantic mapping snapshot fields have invalid types.")
        if not isinstance(covariates, list) or not all(
            isinstance(name, str) for name in covariates
        ):
            raise InvalidAnalysisRunError("Semantic mapping snapshot fields have invalid types.")
        return cls.create(
            time_column=values["time_column"],
            unit_column=values["unit_column"],
            treatment_column=values["treatment_column"],
            outcome_column=values["outcome_column"],
            spend_column=spend,
            covariate_columns=covariates,
            treatment_value=values["treatment_value"],
            control_value=values["control_value"],
        )

    @classmethod
    def from_json(cls, serialized: str) -> Self:
        if not serialized.strip():
            raise InvalidAnalysisRunError("Semantic mapping snapshot must not be blank.")
        try:
            parsed = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise InvalidAnalysisRunError(
                "Semantic mapping snapshot must be valid JSON."
            ) from error
        if not isinstance(parsed, dict):
            raise InvalidAnalysisRunError("Semantic mapping snapshot must be a JSON object.")
        return cls.from_mapping(parsed)

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "time_column": self.time_column,
            "unit_column": self.unit_column,
            "treatment_column": self.treatment_column,
            "outcome_column": self.outcome_column,
            "spend_column": self.spend_column,
            "covariate_columns": list(self.covariate_columns),
            "treatment_value": self.treatment_value,
            "control_value": self.control_value,
        }

    @staticmethod
    def _normalize_column(value: str) -> str:
        normalized = value.strip().casefold()
        if not normalized:
            raise InvalidAnalysisRunError("Mapped column name must not be blank.")
        if len(normalized) > _MAX_VALUE_LENGTH:
            raise InvalidAnalysisRunError("Mapped column name must not exceed 255 characters.")
        return normalized

    @staticmethod
    def _normalize_value(value: str, *, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise InvalidAnalysisRunError(f"{field_name} must not be blank.")
        if len(normalized) > _MAX_VALUE_LENGTH:
            raise InvalidAnalysisRunError(f"{field_name} must not exceed 255 characters.")
        return normalized
