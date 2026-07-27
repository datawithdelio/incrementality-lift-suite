from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol


class GeographyMapping(Protocol):
    @property
    def version(self) -> int: ...

    @property
    def unit_column(self) -> str: ...

    @property
    def outcome_column(self) -> str: ...

    @property
    def spend_column(self) -> str | None: ...

    @property
    def covariate_columns(self) -> Sequence[str]: ...


@dataclass(frozen=True, slots=True)
class GeographyMetrics:
    outcome_sum: float | None
    spend_sum: float | None
    covariate_sums: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class GeographySummaryItem:
    value: str
    observation_count: int
    latitude: float | None
    longitude: float | None
    coordinate_status: str
    metrics: GeographyMetrics


@dataclass(frozen=True, slots=True)
class GeographySummaryResult:
    mapping_version: int
    unit_column: str
    total_geographies: int
    geographies: tuple[GeographySummaryItem, ...]


@dataclass(slots=True)
class _Accumulator:
    observation_count: int = 0
    outcome_sum: float = 0.0
    outcome_count: int = 0
    spend_sum: float = 0.0
    spend_count: int = 0
    latitude: float | None = None
    longitude: float | None = None
    covariate_sums: dict[str, float] | None = None

    def __post_init__(self) -> None:
        if self.covariate_sums is None:
            self.covariate_sums = {}


def _number(value: object) -> float | None:
    if value is None:
        return None

    raw = str(value).strip()

    if not raw:
        return None

    try:
        parsed = float(raw)
    except ValueError:
        return None

    return parsed if isfinite(parsed) else None


def _coordinate(
    row: Mapping[str, object],
    names: tuple[str, ...],
    *,
    minimum: float,
    maximum: float,
) -> float | None:
    for name in names:
        value = _number(row.get(name))

        if value is not None and minimum <= value <= maximum:
            return value

    return None


class GeographySummaryBuilder:
    """Build complete geography evidence from canonical dataset rows."""

    def build(
        self,
        rows: Sequence[Mapping[str, object]],
        mapping: GeographyMapping,
    ) -> GeographySummaryResult:
        accumulators: dict[str, _Accumulator] = defaultdict(_Accumulator)

        covariate_columns = tuple(
            column
            for column in mapping.covariate_columns
            if column not in {
                mapping.outcome_column,
                mapping.spend_column,
            }
        )

        for row in rows:
            geography = str(
                row.get(mapping.unit_column, ""),
            ).strip()

            if not geography:
                continue

            accumulator = accumulators[geography]
            accumulator.observation_count += 1

            outcome = _number(
                row.get(mapping.outcome_column),
            )

            if outcome is not None:
                accumulator.outcome_sum += outcome
                accumulator.outcome_count += 1

            if mapping.spend_column:
                spend = _number(
                    row.get(mapping.spend_column),
                )

                if spend is not None:
                    accumulator.spend_sum += spend
                    accumulator.spend_count += 1

            for column in covariate_columns:
                value = _number(row.get(column))

                if value is not None:
                    assert accumulator.covariate_sums is not None
                    accumulator.covariate_sums[column] = (
                        accumulator.covariate_sums.get(column, 0.0)
                        + value
                    )

            latitude = _coordinate(
                row,
                ("latitude", "lat"),
                minimum=-90,
                maximum=90,
            )

            longitude = _coordinate(
                row,
                ("longitude", "lon", "lng"),
                minimum=-180,
                maximum=180,
            )

            if latitude is not None and longitude is not None:
                if accumulator.latitude is None:
                    accumulator.latitude = latitude
                    accumulator.longitude = longitude
                elif (
                    accumulator.latitude != latitude
                    or accumulator.longitude != longitude
                ):
                    # Conflicting coordinates are not silently accepted.
                    accumulator.latitude = None
                    accumulator.longitude = None

        geographies = tuple(
            GeographySummaryItem(
                value=value,
                observation_count=accumulator.observation_count,
                latitude=accumulator.latitude,
                longitude=accumulator.longitude,
                coordinate_status=(
                    "verified"
                    if accumulator.latitude is not None
                    and accumulator.longitude is not None
                    else "missing"
                ),
                metrics=GeographyMetrics(
                    outcome_sum=(
                        accumulator.outcome_sum
                        if accumulator.outcome_count
                        else None
                    ),
                    spend_sum=(
                        accumulator.spend_sum
                        if accumulator.spend_count
                        else None
                    ),
                    covariate_sums=dict(
                        sorted(
                            (
                                accumulator.covariate_sums
                                or {}
                            ).items(),
                        ),
                    ),
                ),
            )
            for value, accumulator in sorted(
                accumulators.items(),
                key=lambda item: item[0].casefold(),
            )
        )

        return GeographySummaryResult(
            mapping_version=mapping.version,
            unit_column=mapping.unit_column,
            total_geographies=len(geographies),
            geographies=geographies,
        )
