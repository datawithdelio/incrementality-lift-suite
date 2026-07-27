import csv
import io
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from statistics import mean, median, quantiles


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
    outcome_column: str | None = None
    intervention_date: str | None = None

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("Page must be positive.")
        if not 1 <= self.page_size <= 500:
            raise ValueError("Dataset page size must be between 1 and 500.")
        if self.intervention_date is not None:
            try:
                date.fromisoformat(self.intervention_date)
            except ValueError as error:
                raise ValueError(
                    "Intervention date must use YYYY-MM-DD format."
                ) from error


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
class ExplorerSemanticMapping:
    time_column: str
    unit_column: str
    treatment_column: str
    outcome_column: str
    treatment_value: str
    control_value: str


@dataclass(frozen=True, slots=True)
class TrendPoint:
    period: str
    treatment_value: float | None
    control_value: float | None
    treatment_observations: int
    control_observations: int
    phase: str


@dataclass(frozen=True, slots=True)
class HistogramBin:
    minimum: float
    maximum: float
    treatment_count: int
    control_count: int


@dataclass(frozen=True, slots=True)
class OutcomeDistribution:
    minimum: float | None
    maximum: float | None
    mean: float | None
    median: float | None
    first_quartile: float | None
    third_quartile: float | None
    outlier_count: int
    sample_size: int
    bins: tuple[HistogramBin, ...]


@dataclass(frozen=True, slots=True)
class MissingnessPoint:
    column: str
    missing_count: int
    missing_percentage: float


@dataclass(frozen=True, slots=True)
class TreatmentBalance:
    treatment_label: str
    treatment_value: str
    treatment_count: int
    treatment_percentage: float
    control_label: str
    control_value: str
    control_count: int
    control_percentage: float
    treatment_pre_count: int
    treatment_post_count: int
    control_pre_count: int
    control_post_count: int
    status: str


@dataclass(frozen=True, slots=True)
class BreakdownPoint:
    value: str
    outcome_mean: float | None
    observation_count: int
    treatment_count: int
    control_count: int


@dataclass(frozen=True, slots=True)
class DatasetVisualizations:
    time_column: str | None
    treatment_column: str | None
    outcome_column: str | None
    treatment_start_date: str | None
    trend: tuple[TrendPoint, ...]
    distribution: OutcomeDistribution
    missingness: tuple[MissingnessPoint, ...]
    balance: TreatmentBalance | None
    breakdowns: dict[str, tuple[BreakdownPoint, ...]]


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
    visualizations: DatasetVisualizations


class DatasetExplorer:
    """Apply server-side filtering, aggregation, sorting, and pagination."""

    def execute(
        self,
        rows: tuple[dict[str, str], ...],
        query: DatasetExplorerQuery,
        mapping: ExplorerSemanticMapping | None = None,
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
        visualizations = self._visualizations(filtered, names, query, mapping)
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
            outcome_distribution=self._legacy_outcome_distribution(visualizations.distribution),
            visualizations=visualizations,
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
            if item.operator == "is_missing" and current.strip():
                return False
            if item.operator not in {"equals", "contains", "is_missing"}:
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

    @classmethod
    def _visualizations(
        cls,
        rows: list[dict[str, str]],
        names: tuple[str, ...],
        query: DatasetExplorerQuery,
        mapping: ExplorerSemanticMapping | None,
    ) -> DatasetVisualizations:
        time_column = cls._column(
            names,
            mapping.time_column if mapping else None,
            ("date", "time"),
        )
        treatment_column = cls._column(
            names,
            mapping.treatment_column if mapping else None,
            ("treat",),
        )
        outcome_column = cls._outcome_column(
            rows,
            names,
            query.outcome_column,
            mapping.outcome_column if mapping else None,
        )
        treatment_value, control_value = cls._treatment_values(
            rows,
            treatment_column,
            mapping,
        )
        post_column = next(
            (
                name
                for name in names
                if "post" in name.casefold()
            ),
            None,
        )
        treatment_start = cls._treatment_start(
            rows,
            time_column,
            post_column,
            query.intervention_date,
        )
        distribution = cls._distribution_summary(
            rows,
            outcome_column,
            treatment_column,
            treatment_value,
            control_value,
        )
        balance = cls._balance(
            rows,
            treatment_column,
            treatment_value,
            control_value,
            time_column,
            treatment_start,
        )
        return DatasetVisualizations(
            time_column=time_column,
            treatment_column=treatment_column,
            outcome_column=outcome_column,
            treatment_start_date=treatment_start,
            trend=cls._trend(
                rows,
                time_column,
                outcome_column,
                treatment_column,
                treatment_value,
                control_value,
                treatment_start,
            ),
            distribution=distribution,
            missingness=cls._missingness(rows, names),
            balance=balance,
            breakdowns=cls._breakdowns(
                rows,
                names,
                outcome_column,
                treatment_column,
                treatment_value,
                control_value,
                time_column,
                post_column,
            ),
        )

    @staticmethod
    def _column(
        names: tuple[str, ...],
        preferred: str | None,
        fragments: tuple[str, ...],
    ) -> str | None:
        if preferred in names:
            return preferred
        return next(
            (
                name
                for name in names
                if any(fragment in name.casefold() for fragment in fragments)
            ),
            None,
        )

    @classmethod
    def _outcome_column(
        cls,
        rows: list[dict[str, str]],
        names: tuple[str, ...],
        selected: str | None,
        mapped: str | None,
    ) -> str | None:
        candidates = (
            selected,
            mapped,
            next(
                (
                    item
                    for item in names
                    if item.casefold() in {"outcome", "revenue", "conversions"}
                ),
                None,
            ),
        )
        for candidate in candidates:
            if candidate in names and cls._numeric_values(rows, candidate):
                return candidate
        return None

    @staticmethod
    def _numeric_values(
        rows: list[dict[str, str]],
        column: str | None,
    ) -> list[float]:
        if column is None:
            return []
        values: list[float] = []
        try:
            for row in rows:
                raw = row[column].strip()
                if raw:
                    values.append(float(raw))
        except (KeyError, ValueError):
            return []
        return values

    @staticmethod
    def _treatment_values(
        rows: list[dict[str, str]],
        column: str | None,
        mapping: ExplorerSemanticMapping | None,
    ) -> tuple[str | None, str | None]:
        if mapping is not None:
            return mapping.treatment_value, mapping.control_value
        if column is None:
            return None, None
        values = tuple(dict.fromkeys(row[column] for row in rows if row[column]))
        treatment = next(
            (
                value
                for value in values
                if value.casefold() in {"1", "yes", "true", "treated", "treatment"}
            ),
            values[-1] if values else None,
        )
        control = next((value for value in values if value != treatment), None)
        return treatment, control

    @staticmethod
    def _is_truthy(value: str) -> bool:
        return value.strip().casefold() in {"1", "yes", "true", "post"}

    @classmethod
    def _treatment_start(
        cls,
        rows: list[dict[str, str]],
        time_column: str | None,
        post_column: str | None,
        explicit: str | None,
    ) -> str | None:
        if time_column is None:
            return None

        available_periods = sorted(
            row[time_column]
            for row in rows
            if row[time_column]
        )

        if explicit is not None:
            if (
                not available_periods
                or explicit < available_periods[0]
                or explicit > available_periods[-1]
            ):
                raise ValueError(
                    "Intervention date must fall inside the dataset date range."
                )
            return explicit

        if post_column is None:
            return None

        periods = [
            row[time_column]
            for row in rows
            if row[time_column] and cls._is_truthy(row[post_column])
        ]
        return min(periods, default=None)

    @classmethod
    def _trend(
        cls,
        rows: list[dict[str, str]],
        time_column: str | None,
        outcome_column: str | None,
        treatment_column: str | None,
        treatment_value: str | None,
        control_value: str | None,
        treatment_start: str | None,
    ) -> tuple[TrendPoint, ...]:
        if (
            time_column is None
            or outcome_column is None
            or treatment_column is None
        ):
            return ()
        aggregates: dict[str, dict[str, list[float]]] = {}
        for row in rows:
            period = row[time_column]
            group = row[treatment_column]
            if not period or group not in {treatment_value, control_value}:
                continue
            try:
                outcome = float(row[outcome_column])
            except ValueError:
                continue
            bucket = aggregates.setdefault(
                period,
                {"treatment": [], "control": []},
            )
            key = "treatment" if group == treatment_value else "control"
            bucket[key].append(outcome)
        return tuple(
            TrendPoint(
                period=period,
                treatment_value=mean(groups["treatment"])
                if groups["treatment"]
                else None,
                control_value=mean(groups["control"])
                if groups["control"]
                else None,
                treatment_observations=len(groups["treatment"]),
                control_observations=len(groups["control"]),
                phase=(
                    "post"
                    if treatment_start is not None and period >= treatment_start
                    else "pre"
                ),
            )
            for period, groups in sorted(aggregates.items())
        )

    @classmethod
    def _distribution_summary(
        cls,
        rows: list[dict[str, str]],
        outcome_column: str | None,
        treatment_column: str | None,
        treatment_value: str | None,
        control_value: str | None,
    ) -> OutcomeDistribution:
        values = cls._numeric_values(rows, outcome_column)
        if not values:
            return OutcomeDistribution(
                None,
                None,
                None,
                None,
                None,
                None,
                0,
                0,
                (),
            )
        ordered = sorted(values)
        if len(ordered) >= 2:
            first_quartile, _, third_quartile = quantiles(
                ordered,
                n=4,
                method="inclusive",
            )
        else:
            first_quartile = third_quartile = ordered[0]
        interquartile_range = third_quartile - first_quartile
        lower = first_quartile - 1.5 * interquartile_range
        upper = third_quartile + 1.5 * interquartile_range
        return OutcomeDistribution(
            minimum=ordered[0],
            maximum=ordered[-1],
            mean=mean(ordered),
            median=median(ordered),
            first_quartile=first_quartile,
            third_quartile=third_quartile,
            outlier_count=sum(value < lower or value > upper for value in ordered),
            sample_size=len(ordered),
            bins=cls._histogram(
                rows,
                outcome_column,
                treatment_column,
                treatment_value,
                control_value,
                ordered[0],
                ordered[-1],
            ),
        )

    @staticmethod
    def _histogram(
        rows: list[dict[str, str]],
        outcome_column: str | None,
        treatment_column: str | None,
        treatment_value: str | None,
        control_value: str | None,
        minimum: float,
        maximum: float,
    ) -> tuple[HistogramBin, ...]:
        if outcome_column is None:
            return ()
        bin_count = min(10, max(1, round(math.sqrt(len(rows)))))
        width = (maximum - minimum) / bin_count if maximum != minimum else 1
        bins = [
            {
                "minimum": minimum + index * width,
                "maximum": maximum
                if index == bin_count - 1
                else minimum + (index + 1) * width,
                "treatment": 0,
                "control": 0,
            }
            for index in range(bin_count)
        ]
        for row in rows:
            raw = row[outcome_column].strip()
            if not raw:
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            index = (
                min(bin_count - 1, int((value - minimum) / width))
                if maximum != minimum
                else 0
            )
            if treatment_column is None:
                bins[index]["control"] += 1
            elif row[treatment_column] == treatment_value:
                bins[index]["treatment"] += 1
            elif row[treatment_column] == control_value:
                bins[index]["control"] += 1
        return tuple(
            HistogramBin(
                minimum=float(item["minimum"]),
                maximum=float(item["maximum"]),
                treatment_count=int(item["treatment"]),
                control_count=int(item["control"]),
            )
            for item in bins
        )

    @staticmethod
    def _missingness(
        rows: list[dict[str, str]],
        names: tuple[str, ...],
    ) -> tuple[MissingnessPoint, ...]:
        total = len(rows)
        return tuple(
            MissingnessPoint(
                column=name,
                missing_count=sum(not row[name].strip() for row in rows),
                missing_percentage=(
                    100 * sum(not row[name].strip() for row in rows) / total
                    if total
                    else 0
                ),
            )
            for name in names
        )

    @classmethod
    def _balance(
        cls,
        rows: list[dict[str, str]],
        treatment_column: str | None,
        treatment_value: str | None,
        control_value: str | None,
        time_column: str | None,
        treatment_start: str | None,
    ) -> TreatmentBalance | None:
        if (
            treatment_column is None
            or treatment_value is None
            or control_value is None
        ):
            return None
        treatment_rows = [
            row
            for row in rows
            if row[treatment_column] == treatment_value
        ]
        control_rows = [
            row
            for row in rows
            if row[treatment_column] == control_value
        ]
        total = len(treatment_rows) + len(control_rows)
        treatment_percentage = 100 * len(treatment_rows) / total if total else 0
        control_percentage = 100 * len(control_rows) / total if total else 0

        def phase_count(
            group: list[dict[str, str]],
            *,
            post: bool,
        ) -> int:
            if time_column is None or treatment_start is None:
                return 0
            return sum(
                (row[time_column] >= treatment_start) is post
                for row in group
                if row[time_column]
            )

        return TreatmentBalance(
            treatment_label="Treatment",
            treatment_value=treatment_value,
            treatment_count=len(treatment_rows),
            treatment_percentage=treatment_percentage,
            control_label="Control",
            control_value=control_value,
            control_count=len(control_rows),
            control_percentage=control_percentage,
            treatment_pre_count=phase_count(treatment_rows, post=False),
            treatment_post_count=phase_count(treatment_rows, post=True),
            control_pre_count=phase_count(control_rows, post=False),
            control_post_count=phase_count(control_rows, post=True),
            status=(
                "Balanced"
                if abs(treatment_percentage - control_percentage) <= 10
                else "Needs review"
            ),
        )

    @classmethod
    def _breakdowns(
        cls,
        rows: list[dict[str, str]],
        names: tuple[str, ...],
        outcome_column: str | None,
        treatment_column: str | None,
        treatment_value: str | None,
        control_value: str | None,
        time_column: str | None,
        post_column: str | None,
    ) -> dict[str, tuple[BreakdownPoint, ...]]:
        if outcome_column is None:
            return {}
        excluded = {
            outcome_column,
            treatment_column,
            time_column,
            post_column,
        }
        breakdowns: dict[str, tuple[BreakdownPoint, ...]] = {}
        for name in names:
            values = {row[name] for row in rows if row[name]}
            if name in excluded or not 2 <= len(values) <= 20:
                continue
            points: list[BreakdownPoint] = []
            for value in sorted(values):
                matching = [row for row in rows if row[name] == value]
                outcomes = cls._numeric_values(matching, outcome_column)
                points.append(
                    BreakdownPoint(
                        value=value,
                        outcome_mean=mean(outcomes) if outcomes else None,
                        observation_count=len(matching),
                        treatment_count=sum(
                            treatment_column is not None
                            and row[treatment_column] == treatment_value
                            for row in matching
                        ),
                        control_count=sum(
                            treatment_column is not None
                            and row[treatment_column] == control_value
                            for row in matching
                        ),
                    )
                )
            breakdowns[name] = tuple(points)
        return breakdowns

    @staticmethod
    def _legacy_outcome_distribution(
        distribution: OutcomeDistribution,
    ) -> dict[str, float]:
        return {
            name: value
            for name, value in {
                "minimum": distribution.minimum,
                "maximum": distribution.maximum,
                "mean": distribution.mean,
                "median": distribution.median,
            }.items()
            if value is not None
        }
