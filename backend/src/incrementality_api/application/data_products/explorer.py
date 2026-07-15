import csv
import io
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from statistics import mean, median


class MalformedDatasetError(ValueError):
    """Dataset rows do not share a stable schema."""


@dataclass(frozen=True, slots=True)
class DatasetFilter:
    column: str
    operator: str
    value: str


@dataclass(frozen=True, slots=True)
class DatasetExplorerQuery:
    page: int = 1
    page_size: int = 50
    sort_column: str | None = None
    descending: bool = False
    filters: tuple[DatasetFilter, ...] = ()
    column_search: str | None = None

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("Page must be positive.")
        if not 1 <= self.page_size <= 500:
            raise ValueError("Dataset page size must be between 1 and 500.")


@dataclass(frozen=True, slots=True)
class ColumnSummary:
    name: str
    inferred_type: str
    missing_percentage: float
    unique_count: int
    minimum: float | str | None
    maximum: float | str | None
    mean: float | None
    median: float | None


@dataclass(frozen=True, slots=True)
class DateRange:
    column: str
    minimum: str
    maximum: str


@dataclass(frozen=True, slots=True)
class DatasetExplorerResult:
    rows: tuple[dict[str, str], ...]
    columns: tuple[ColumnSummary, ...]
    total_rows: int
    page: int
    page_size: int
    total_pages: int
    date_range: DateRange | None
    treatment_distribution: dict[str, int]
    outcome_distribution: dict[str, float]


class DatasetExplorer:
    """Apply server-side filtering, aggregation, sorting, and pagination."""

    def execute(
        self, rows: tuple[dict[str, str], ...], query: DatasetExplorerQuery
    ) -> DatasetExplorerResult:
        names = self._validate(rows)
        filtered = [row for row in rows if self._matches(row, query.filters)]
        if query.sort_column:
            sort_column = query.sort_column
            if sort_column not in names:
                raise ValueError("Sort column is unavailable.")
            filtered.sort(
                key=lambda row: self._sort_value(row[sort_column]),
                reverse=query.descending,
            )
        selected_names = tuple(
            name
            for name in names
            if not query.column_search or query.column_search.casefold() in name.casefold()
        )
        start = (query.page - 1) * query.page_size
        page_rows = tuple(
            {name: row[name] for name in selected_names}
            for row in filtered[start : start + query.page_size]
        )
        return DatasetExplorerResult(
            rows=page_rows,
            columns=tuple(self._profile(name, filtered) for name in selected_names),
            total_rows=len(filtered),
            page=query.page,
            page_size=query.page_size,
            total_pages=math.ceil(len(filtered) / query.page_size) if filtered else 0,
            date_range=self._date_range(names, filtered),
            treatment_distribution=self._distribution(
                filtered, next((name for name in names if "treat" in name), None)
            ),
            outcome_distribution=self._outcome_distribution(filtered, names),
        )

    def export_csv(self, rows: tuple[dict[str, str], ...], query: DatasetExplorerQuery) -> bytes:
        names = self._validate(rows)
        selected_names = tuple(
            name
            for name in names
            if not query.column_search or query.column_search.casefold() in name.casefold()
        )
        filtered = [row for row in rows if self._matches(row, query.filters)]
        if query.sort_column:
            sort_column = query.sort_column
            if sort_column not in names:
                raise ValueError("Sort column is unavailable.")
            filtered.sort(
                key=lambda row: self._sort_value(row[sort_column]),
                reverse=query.descending,
            )
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=selected_names)
        writer.writeheader()
        writer.writerows({name: row[name] for name in selected_names} for row in filtered)
        return output.getvalue().encode()

    @staticmethod
    def _validate(rows: tuple[dict[str, str], ...]) -> tuple[str, ...]:
        if not rows:
            return ()
        names = tuple(rows[0])
        if not names or any(tuple(row) != names for row in rows):
            raise MalformedDatasetError("Dataset rows have inconsistent columns.")
        return names

    @staticmethod
    def _matches(row: dict[str, str], filters: tuple[DatasetFilter, ...]) -> bool:
        for item in filters:
            current = row.get(item.column)
            if current is None:
                return False
            if item.operator == "equals" and current != item.value:
                return False
            if item.operator == "contains" and item.value.casefold() not in current.casefold():
                return False
            if item.operator not in {"equals", "contains"}:
                raise ValueError("Dataset filter operator is unsupported.")
        return True

    @staticmethod
    def _sort_value(value: str) -> tuple[int, float | str]:
        try:
            return (0, float(value))
        except ValueError:
            return (1, value.casefold())

    @classmethod
    def _profile(cls, name: str, rows: list[dict[str, str]]) -> ColumnSummary:
        values = [row[name].strip() for row in rows]
        present = [value for value in values if value]
        inferred = cls._infer(present)
        numeric = [float(value) for value in present] if inferred in {"integer", "float"} else []
        return ColumnSummary(
            name=name,
            inferred_type=inferred,
            missing_percentage=(100 * (len(values) - len(present)) / len(values)) if values else 0,
            unique_count=len(set(present)),
            minimum=(min(numeric) if numeric else min(present, default=None)),
            maximum=(max(numeric) if numeric else max(present, default=None)),
            mean=mean(numeric) if numeric else None,
            median=median(numeric) if numeric else None,
        )

    @staticmethod
    def _infer(values: list[str]) -> str:
        if not values:
            return "string"
        lowered = {value.casefold() for value in values}
        if lowered <= {"true", "false", "yes", "no", "0", "1"}:
            return "boolean"
        try:
            integers = all(float(value).is_integer() for value in values)
            return "integer" if integers else "float"
        except ValueError:
            pass
        try:
            parsed = [datetime.fromisoformat(value) for value in values]
            return (
                "date" if all(item.time() == datetime.min.time() for item in parsed) else "datetime"
            )
        except ValueError:
            return "string"

    @staticmethod
    def _date_range(names: tuple[str, ...], rows: list[dict[str, str]]) -> DateRange | None:
        for name in names:
            values = [row[name] for row in rows if row[name]]
            try:
                dates = [date.fromisoformat(value[:10]) for value in values]
            except ValueError:
                continue
            if dates:
                return DateRange(name, min(dates).isoformat(), max(dates).isoformat())
        return None

    @staticmethod
    def _distribution(rows: list[dict[str, str]], name: str | None) -> dict[str, int]:
        return dict(Counter(row[name] for row in rows)) if name else {}

    @staticmethod
    def _outcome_distribution(
        rows: list[dict[str, str]], names: tuple[str, ...]
    ) -> dict[str, float]:
        name = next((item for item in names if item in {"outcome", "revenue", "conversions"}), None)
        if not name:
            return {}
        try:
            values = [float(row[name]) for row in rows if row[name]]
        except ValueError:
            return {}
        return (
            {"minimum": min(values), "maximum": max(values), "mean": mean(values)} if values else {}
        )
