import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from statistics import median
from typing import Protocol

from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType


@dataclass(frozen=True, slots=True)
class MarketingMixDesignSummary:
    period_count: int
    saturation_half_spend_defaults: dict[str, float]


class MarketingMixDesignSummaryBuilder:
    """Summarize MMM media spend at the estimator's time-period grain."""

    def build(
        self,
        *,
        rows: tuple[Mapping[str, str], ...],
        time_column: str,
        media_channels: tuple[str, ...],
    ) -> MarketingMixDesignSummary:
        if not time_column.strip():
            raise ValueError("MMM design summary requires a time column.")

        if not media_channels:
            raise ValueError("MMM design summary requires media channels.")

        grouped_spend: defaultdict[str, dict[str, float]] = defaultdict(
            lambda: {channel: 0.0 for channel in media_channels}
        )

        for row_number, row in enumerate(rows, start=2):
            try:
                period = str(row[time_column]).strip()

                if not period:
                    raise ValueError

                values = {
                    channel: float(str(row[channel]).strip())
                    for channel in media_channels
                }
            except (KeyError, ValueError) as error:
                raise ValueError(
                    f"CSV row {row_number} has invalid MMM design-summary values."
                ) from error

            if any(
                not math.isfinite(value) or value < 0
                for value in values.values()
            ):
                raise ValueError(
                    f"CSV row {row_number} has invalid MMM design-summary values."
                )

            for channel, value in values.items():
                grouped_spend[period][channel] += value

        defaults: dict[str, float] = {}

        for channel in media_channels:
            period_totals = [
                values[channel]
                for _, values in sorted(grouped_spend.items())
            ]

            if not period_totals:
                continue

            channel_median = float(median(period_totals))

            # Half-spend must be strictly positive. Do not invent a fallback.
            if channel_median > 0:
                defaults[channel] = channel_median

        return MarketingMixDesignSummary(
            period_count=len(grouped_spend),
            saturation_half_spend_defaults=defaults,
        )



class AnalysisPeriodFilter(Protocol):
    def filter(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        time_column: str,
        snapshot: AnalysisPeriodSnapshot | None,
    ) -> tuple[dict[str, str], ...]: ...


class AnalysisSelectionFilter(Protocol):
    def filter(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        snapshot: AnalysisSelectionSnapshot,
    ) -> tuple[dict[str, str], ...]: ...


class MarketingMixDesignSummaryPlanner:
    """Apply the analysis population contract before deriving MMM defaults."""

    def __init__(
        self,
        *,
        period_filter: AnalysisPeriodFilter,
        selection_executor: AnalysisSelectionFilter,
        summary_builder: MarketingMixDesignSummaryBuilder,
    ) -> None:
        self._period_filter = period_filter
        self._selection_executor = selection_executor
        self._summary_builder = summary_builder

    def build_from_configuration(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        mapping: SemanticMappingSnapshot,
        configuration: Mapping[str, object],
    ) -> MarketingMixDesignSummary:
        configured_channels = configuration.get("media_channels")

        if (
            not isinstance(configured_channels, list)
            or not configured_channels
            or not all(
                isinstance(channel, str) and channel.strip()
                for channel in configured_channels
            )
        ):
            raise ValueError(
                "MMM media_channels must be a non-empty string list."
            )

        channels = tuple(str(channel) for channel in configured_channels)

        if len(set(channels)) != len(channels):
            raise ValueError("MMM media_channels must be unique.")

        configured_controls = configuration.get("control_columns", [])
        if (
            not isinstance(configured_controls, list)
            or not all(
                isinstance(control, str) and control.strip()
                for control in configured_controls
            )
        ):
            raise ValueError("MMM control_columns must be a string list.")

        controls = tuple(str(control) for control in configured_controls)

        if len(set(controls)) != len(controls):
            raise ValueError("MMM control_columns must be unique.")

        if set(channels).intersection(controls):
            raise ValueError(
                "MMM media channels and controls must not overlap."
            )

        aggregate_spend_column = configuration.get(
            "aggregate_spend_column",
            mapping.spend_column,
        )
        if aggregate_spend_column in channels:
            raise ValueError(
                "MMM aggregate spend must not be configured as a media channel."
            )

        period = AnalysisPeriodSnapshot.from_configuration(
            AnalysisEstimatorType.MARKETING_MIX_MODEL,
            configuration,
        )
        selection = AnalysisSelectionSnapshot.from_configuration(
            estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
            configuration=configuration,
            semantic_mapping=mapping,
        )

        return self.build(
            rows=rows,
            mapping=mapping,
            period=period,
            selection=selection,
            media_channels=channels,
        )

    def build(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        mapping: SemanticMappingSnapshot,
        period: AnalysisPeriodSnapshot,
        selection: AnalysisSelectionSnapshot,
        media_channels: tuple[str, ...],
    ) -> MarketingMixDesignSummary:
        selected_rows = self._period_filter.filter(
            rows=rows,
            time_column=mapping.time_column,
            snapshot=period,
        )
        selected_rows = self._selection_executor.filter(
            rows=selected_rows,
            snapshot=selection,
        )

        if not selected_rows:
            raise ValueError("No dataset rows match the MMM design-summary selection.")

        return self._summary_builder.build(
            rows=selected_rows,
            time_column=mapping.time_column,
            media_channels=media_channels,
        )
