import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Self

from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

_SELECTION_FIELDS = {
    "row_filters",
    "included_values",
    "excluded_values",
    "selected_geographies",
    "excluded_geographies",
    "segment_column",
    "selected_segments",
    "excluded_segments",
    "eligibility_filters",
}
_SERIALIZED_FIELDS = _SELECTION_FIELDS | {"geography_column"}
_VALUE_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
}
_NULL_OPERATORS = {"is_null", "is_not_null"}
_ORDERED_OPERATORS = {
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
}
_VALUE_TYPES = {"string", "number", "boolean", "date", "null"}


@dataclass(frozen=True, slots=True)
class SelectionValue:
    """A typed, canonical filter value."""

    value_type: str
    value: str | int | float | bool | None

    @classmethod
    def from_object(cls, raw: object) -> Self:
        if not isinstance(raw, dict) or set(raw) != {"type", "value"}:
            raise InvalidAnalysisRunError("Selection values must contain exactly type and value.")
        value_type = raw["type"]
        if not isinstance(value_type, str) or value_type not in _VALUE_TYPES:
            raise InvalidAnalysisRunError("Selection value type is unsupported.")
        value = raw["value"]
        if value_type == "string":
            if not isinstance(value, str) or not value.strip():
                raise InvalidAnalysisRunError("Selection string values must not be blank.")
            return cls(value_type, value.strip())
        if value_type == "number":
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise InvalidAnalysisRunError("Selection number values must be numeric.")
            if not math.isfinite(float(value)):
                raise InvalidAnalysisRunError("Selection number values must be finite.")
            normalized: int | float = int(value) if float(value).is_integer() else float(value)
            return cls(value_type, normalized)
        if value_type == "boolean":
            if not isinstance(value, bool):
                raise InvalidAnalysisRunError("Selection boolean values must be boolean.")
            return cls(value_type, value)
        if value_type == "date":
            if not isinstance(value, str) or not value.strip():
                raise InvalidAnalysisRunError("Selection date values must be ISO dates.")
            try:
                normalized_date = date.fromisoformat(value.strip())
            except ValueError as error:
                raise InvalidAnalysisRunError("Selection date values must be ISO dates.") from error
            return cls(value_type, normalized_date.isoformat())
        if value is not None:
            raise InvalidAnalysisRunError("Selection null values must contain null.")
        return cls(value_type, None)

    def as_dict(self) -> dict[str, object]:
        return {"type": self.value_type, "value": self.value}

    @property
    def canonical_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class SelectionRule:
    """One canonical predicate applied to a dataset row."""

    column: str
    operator: str
    value: SelectionValue | None

    @classmethod
    def from_object(cls, raw: object) -> Self:
        if not isinstance(raw, dict):
            raise InvalidAnalysisRunError("Selection filters must be JSON objects.")
        operator = raw.get("operator")
        if not isinstance(operator, str) or not operator.strip():
            raise InvalidAnalysisRunError("Selection filter operator must not be empty.")
        normalized_operator = operator.strip()
        if normalized_operator not in _VALUE_OPERATORS | _NULL_OPERATORS:
            raise InvalidAnalysisRunError("Selection filter operator is unsupported.")
        column = _field_name(raw.get("column"), "Selection filter column")
        if normalized_operator in _NULL_OPERATORS:
            if set(raw) != {"column", "operator"}:
                raise InvalidAnalysisRunError(
                    f"Selection operator '{normalized_operator}' must not have a value."
                )
            return cls(column, normalized_operator, None)
        if set(raw) != {"column", "operator", "value"}:
            raise InvalidAnalysisRunError(
                f"Selection operator '{normalized_operator}' requires one typed value."
            )
        value = SelectionValue.from_object(raw["value"])
        if value.value_type == "null":
            raise InvalidAnalysisRunError("Use is_null or is_not_null for null values.")
        if normalized_operator == "contains" and value.value_type != "string":
            raise InvalidAnalysisRunError("Selection contains requires a string value.")
        if normalized_operator in _ORDERED_OPERATORS and value.value_type not in {
            "string",
            "number",
            "date",
        }:
            raise InvalidAnalysisRunError(
                "Ordered selection operators require a string, number, or date value."
            )
        return cls(column, normalized_operator, value)

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"column": self.column, "operator": self.operator}
        if self.value is not None:
            result["value"] = self.value.as_dict()
        return result

    @property
    def canonical_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class AnalysisSelectionSnapshot:
    """Immutable dataset-selection criteria used by an analysis run."""

    row_filters: tuple[SelectionRule, ...]
    included_values: tuple[tuple[str, tuple[SelectionValue, ...]], ...]
    excluded_values: tuple[tuple[str, tuple[SelectionValue, ...]], ...]
    geography_column: str | None
    selected_geographies: tuple[str, ...]
    excluded_geographies: tuple[str, ...]
    segment_column: str | None
    selected_segments: tuple[str, ...]
    excluded_segments: tuple[str, ...]
    eligibility_filters: tuple[SelectionRule, ...]

    @classmethod
    def from_configuration(
        cls,
        *,
        estimator_type: AnalysisEstimatorType,
        configuration: Mapping[str, object],
        semantic_mapping: SemanticMappingSnapshot,
    ) -> Self:
        del estimator_type
        selected_geographies = _string_collection(
            configuration.get("selected_geographies", []), "selected geographies"
        )
        excluded_geographies = _string_collection(
            configuration.get("excluded_geographies", []), "excluded geographies"
        )
        geography_column = (
            semantic_mapping.unit_column if selected_geographies or excluded_geographies else None
        )
        return cls._create(
            row_filters=_rules(configuration.get("row_filters", []), "row filters"),
            included_values=_value_map(configuration.get("included_values", {}), "included values"),
            excluded_values=_value_map(configuration.get("excluded_values", {}), "excluded values"),
            geography_column=geography_column,
            selected_geographies=selected_geographies,
            excluded_geographies=excluded_geographies,
            segment_column=_segment_column(configuration),
            selected_segments=_string_collection(
                configuration.get("selected_segments", []), "selected segments"
            ),
            excluded_segments=_string_collection(
                configuration.get("excluded_segments", []), "excluded segments"
            ),
            eligibility_filters=_rules(
                configuration.get("eligibility_filters", []), "eligibility filters"
            ),
        )

    @classmethod
    def from_configuration_json(
        cls,
        *,
        estimator_type: AnalysisEstimatorType,
        serialized: str,
        semantic_mapping: SemanticMappingSnapshot,
    ) -> Self:
        if not serialized.strip():
            raise InvalidAnalysisRunError("Analysis configuration must not be blank.")
        try:
            configuration = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise InvalidAnalysisRunError("Analysis configuration must be valid JSON.") from error
        if not isinstance(configuration, dict):
            raise InvalidAnalysisRunError("Analysis configuration must be a JSON object.")
        return cls.from_configuration(
            estimator_type=estimator_type,
            configuration=configuration,
            semantic_mapping=semantic_mapping,
        )

    @classmethod
    def from_json(cls, serialized: str) -> Self:
        if not serialized.strip():
            raise InvalidAnalysisRunError("Analysis-selection snapshot must not be blank.")
        try:
            parsed = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise InvalidAnalysisRunError(
                "Analysis-selection snapshot must be valid JSON."
            ) from error
        if not isinstance(parsed, dict):
            raise InvalidAnalysisRunError("Analysis-selection snapshot must be a JSON object.")
        if set(parsed) != _SERIALIZED_FIELDS:
            raise InvalidAnalysisRunError("Analysis-selection snapshot has invalid fields.")
        geography_column = parsed["geography_column"]
        if geography_column is not None:
            geography_column = _field_name(geography_column, "Geography column")
        segment_column = parsed["segment_column"]
        if segment_column is not None:
            segment_column = _field_name(segment_column, "Segment column")
        return cls._create(
            row_filters=_rules(parsed["row_filters"], "row filters"),
            included_values=_value_map(parsed["included_values"], "included values"),
            excluded_values=_value_map(parsed["excluded_values"], "excluded values"),
            geography_column=geography_column,
            selected_geographies=_string_collection(
                parsed["selected_geographies"], "selected geographies"
            ),
            excluded_geographies=_string_collection(
                parsed["excluded_geographies"], "excluded geographies"
            ),
            segment_column=segment_column,
            selected_segments=_string_collection(parsed["selected_segments"], "selected segments"),
            excluded_segments=_string_collection(parsed["excluded_segments"], "excluded segments"),
            eligibility_filters=_rules(parsed["eligibility_filters"], "eligibility filters"),
        )

    @classmethod
    def _create(
        cls,
        *,
        row_filters: tuple[SelectionRule, ...],
        included_values: tuple[tuple[str, tuple[SelectionValue, ...]], ...],
        excluded_values: tuple[tuple[str, tuple[SelectionValue, ...]], ...],
        geography_column: str | None,
        selected_geographies: tuple[str, ...],
        excluded_geographies: tuple[str, ...],
        segment_column: str | None,
        selected_segments: tuple[str, ...],
        excluded_segments: tuple[str, ...],
        eligibility_filters: tuple[SelectionRule, ...],
    ) -> Self:
        _reject_overlap(
            selected_geographies,
            excluded_geographies,
            "Geography values cannot be both included and excluded.",
        )
        _reject_overlap(
            selected_segments,
            excluded_segments,
            "Segment values cannot be both included and excluded.",
        )
        if (selected_geographies or excluded_geographies) and geography_column is None:
            raise InvalidAnalysisRunError("Geography selections require a geography column.")
        if (selected_segments or excluded_segments) and segment_column is None:
            raise InvalidAnalysisRunError("Segment selections require segment_column.")
        included = dict(included_values)
        excluded = dict(excluded_values)
        for column in included.keys() & excluded.keys():
            if {value.canonical_json for value in included[column]} & {
                value.canonical_json for value in excluded[column]
            }:
                raise InvalidAnalysisRunError(
                    f"Values for '{column}' cannot be both included and excluded."
                )
        return cls(
            row_filters,
            included_values,
            excluded_values,
            geography_column,
            selected_geographies,
            excluded_geographies,
            segment_column,
            selected_segments,
            excluded_segments,
            eligibility_filters,
        )

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "row_filters": [rule.as_dict() for rule in self.row_filters],
            "included_values": _serialize_value_map(self.included_values),
            "excluded_values": _serialize_value_map(self.excluded_values),
            "geography_column": self.geography_column,
            "selected_geographies": list(self.selected_geographies),
            "excluded_geographies": list(self.excluded_geographies),
            "segment_column": self.segment_column,
            "selected_segments": list(self.selected_segments),
            "excluded_segments": list(self.excluded_segments),
            "eligibility_filters": [rule.as_dict() for rule in self.eligibility_filters],
        }

    def canonicalize_configuration(self, configuration: Mapping[str, object]) -> dict[str, object]:
        canonical = {
            key: value for key, value in configuration.items() if key not in _SELECTION_FIELDS
        }
        values = self.as_dict()
        for key in _SELECTION_FIELDS:
            value = values[key]
            if value not in (None, [], {}):
                canonical[key] = value
        return canonical


def _field_name(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise InvalidAnalysisRunError(f"{label} field name must not be blank.")
    return raw.strip()


def _segment_column(configuration: Mapping[str, object]) -> str | None:
    raw = configuration.get("segment_column")
    if raw is None:
        return None
    return _field_name(raw, "Segment column")


def _string_collection(raw: object, label: str) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise InvalidAnalysisRunError(f"Analysis {label} must be a list.")
    normalized: list[str] = []
    for value in raw:
        if not isinstance(value, str) or not value.strip():
            raise InvalidAnalysisRunError(f"Analysis {label} must not contain blank values.")
        normalized.append(value.strip())
    if len(normalized) != len(set(normalized)):
        raise InvalidAnalysisRunError(f"Analysis {label} contains a duplicate value.")
    return tuple(sorted(normalized))


def _rules(raw: object, label: str) -> tuple[SelectionRule, ...]:
    if not isinstance(raw, list):
        raise InvalidAnalysisRunError(f"Analysis {label} must be a list.")
    parsed = [SelectionRule.from_object(value) for value in raw]
    keys = [rule.canonical_json for rule in parsed]
    if len(keys) != len(set(keys)):
        raise InvalidAnalysisRunError(f"Analysis {label} contains a duplicate rule.")
    return tuple(rule for _, rule in sorted(zip(keys, parsed, strict=True)))


def _value_map(raw: object, label: str) -> tuple[tuple[str, tuple[SelectionValue, ...]], ...]:
    if not isinstance(raw, dict):
        raise InvalidAnalysisRunError(f"Analysis {label} must be a JSON object.")
    parsed: list[tuple[str, tuple[SelectionValue, ...]]] = []
    for raw_column, raw_values in raw.items():
        column = _field_name(raw_column, "Selection")
        if not isinstance(raw_values, list) or not raw_values:
            raise InvalidAnalysisRunError(
                f"Analysis {label} for '{column}' must contain at least one value."
            )
        values = [SelectionValue.from_object(value) for value in raw_values]
        keys = [value.canonical_json for value in values]
        if len(keys) != len(set(keys)):
            raise InvalidAnalysisRunError(
                f"Analysis {label} for '{column}' contains a duplicate value."
            )
        parsed.append((column, tuple(value for _, value in sorted(zip(keys, values, strict=True)))))
    return tuple(sorted(parsed, key=lambda item: item[0]))


def _reject_overlap(included: Sequence[str], excluded: Sequence[str], message: str) -> None:
    if set(included) & set(excluded):
        raise InvalidAnalysisRunError(message)


def _serialize_value_map(
    values: tuple[tuple[str, tuple[SelectionValue, ...]], ...],
) -> dict[str, list[dict[str, object]]]:
    return {
        column: [value.as_dict() for value in selected_values] for column, selected_values in values
    }
