from datetime import date

from incrementality_api.application.analysis_execution.estimation import (
    PermanentEstimationError,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
    SelectionRule,
    SelectionValue,
)


class AnalysisSelectionRowExecutor:
    """Apply one persisted analysis-selection snapshot to CSV rows."""

    def filter(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        snapshot: AnalysisSelectionSnapshot,
    ) -> tuple[dict[str, str], ...]:
        if rows:
            available = set(rows[0])
            missing = sorted(self._required_columns(snapshot) - available)
            if missing:
                raise PermanentEstimationError(
                    f"Analysis selection targets unavailable column '{missing[0]}'."
                )
        return tuple(row for row in rows if self._matches(row, snapshot))

    @staticmethod
    def _required_columns(snapshot: AnalysisSelectionSnapshot) -> set[str]:
        columns = {
            rule.column
            for rule in (*snapshot.row_filters, *snapshot.eligibility_filters)
        }
        columns.update(column for column, _values in snapshot.included_values)
        columns.update(column for column, _values in snapshot.excluded_values)
        if snapshot.geography_column is not None:
            columns.add(snapshot.geography_column)
        if snapshot.segment_column is not None:
            columns.add(snapshot.segment_column)
        return columns

    def _matches(
        self, row: dict[str, str], snapshot: AnalysisSelectionSnapshot
    ) -> bool:
        if not all(
            self._matches_rule(row, rule)
            for rule in (*snapshot.row_filters, *snapshot.eligibility_filters)
        ):
            return False
        if not self._matches_value_maps(
            row, snapshot.included_values, snapshot.excluded_values
        ):
            return False
        if snapshot.geography_column is not None and not self._matches_strings(
            row.get(snapshot.geography_column),
            snapshot.selected_geographies,
            snapshot.excluded_geographies,
        ):
            return False
        return snapshot.segment_column is None or self._matches_strings(
            row.get(snapshot.segment_column),
            snapshot.selected_segments,
            snapshot.excluded_segments,
        )

    def _matches_value_maps(
        self,
        row: dict[str, str],
        included: tuple[tuple[str, tuple[SelectionValue, ...]], ...],
        excluded: tuple[tuple[str, tuple[SelectionValue, ...]], ...],
    ) -> bool:
        for column, values in included:
            if not any(self._equals(row.get(column), value) for value in values):
                return False
        for column, values in excluded:
            if any(self._equals(row.get(column), value) for value in values):
                return False
        return True

    @staticmethod
    def _matches_strings(
        raw: str | None, included: tuple[str, ...], excluded: tuple[str, ...]
    ) -> bool:
        value = raw.strip() if raw is not None else None
        return (not included or value in included) and value not in excluded

    def _matches_rule(self, row: dict[str, str], rule: SelectionRule) -> bool:
        raw = row.get(rule.column)
        if rule.operator == "is_null":
            return raw is None or not raw.strip()
        if rule.operator == "is_not_null":
            return raw is not None and bool(raw.strip())
        value = rule.value
        if value is None:
            return False
        if rule.operator == "equals":
            return self._equals(raw, value)
        if rule.operator == "not_equals":
            return not self._equals(raw, value)
        if rule.operator == "contains":
            return (
                raw is not None
                and isinstance(value.value, str)
                and value.value.casefold() in raw.strip().casefold()
            )
        current = self._typed_value(raw, value.value_type)
        expected = value.value
        if current is None or expected is None:
            return False
        if isinstance(current, str) and isinstance(expected, str):
            return self._compare_strings(current, expected, rule.operator)
        if (
            isinstance(current, int | float)
            and not isinstance(current, bool)
            and isinstance(expected, int | float)
            and not isinstance(expected, bool)
        ):
            return self._compare_numbers(float(current), float(expected), rule.operator)
        return False

    def _equals(self, raw: str | None, expected: SelectionValue) -> bool:
        if expected.value_type == "null":
            return raw is None or not raw.strip()
        return self._typed_value(raw, expected.value_type) == expected.value

    @staticmethod
    def _typed_value(
        raw: str | None, value_type: str
    ) -> str | int | float | bool | None:
        if raw is None or not raw.strip():
            return None
        normalized = raw.strip()
        try:
            if value_type == "number":
                number = float(normalized)
                return int(number) if number.is_integer() else number
            if value_type == "boolean":
                lowered = normalized.casefold()
                if lowered in {"true", "yes", "1"}:
                    return True
                if lowered in {"false", "no", "0"}:
                    return False
                return None
            if value_type == "date":
                return date.fromisoformat(normalized).isoformat()
        except ValueError:
            return None
        return normalized

    @staticmethod
    def _compare_strings(left: str, right: str, operator: str) -> bool:
        if operator == "greater_than":
            return left > right
        if operator == "greater_than_or_equal":
            return left >= right
        if operator == "less_than":
            return left < right
        return operator == "less_than_or_equal" and left <= right

    @staticmethod
    def _compare_numbers(left: float, right: float, operator: str) -> bool:
        if operator == "greater_than":
            return left > right
        if operator == "greater_than_or_equal":
            return left >= right
        if operator == "less_than":
            return left < right
        return operator == "less_than_or_equal" and left <= right
