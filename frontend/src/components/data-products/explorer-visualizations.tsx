"use client";

import { DownloadSimpleIcon } from "@phosphor-icons/react/DownloadSimple";
import { forwardRef, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import type {
  BreakdownPoint,
  ColumnSummary,
  DatasetVisualizations,
  HistogramBin,
  MissingnessPoint,
  OutcomeDistribution,
  TreatmentBalance,
  TrendPoint,
} from "@/lib/data-products/types";

export type VisualizationTab =
  | "trend"
  | "distribution"
  | "missingness"
  | "breakdown";

const CHART_WIDTH = 760;
const CHART_HEIGHT = 292;
const PLOT = {
  left: 56,
  right: 24,
  top: 28,
  bottom: 44,
};

function number(value: number | null): string {
  return value === null
    ? "Not available"
    : new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 2,
      }).format(value);
}

function signedNumber(value: number | null): string {
  if (value === null) {
    return "Not available";
  }

  return `${value > 0 ? "+" : ""}${number(value)}`;
}

function date(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value.slice(0, 10)}T00:00:00Z`));
}

function label(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function chartScale(values: number[]): {
  minimum: number;
  maximum: number;
  y: (value: number) => number;
} {
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const span = Math.max(1, maximum - minimum);
  const padding = span * 0.12;
  const low = minimum - padding;
  const high = maximum + padding;
  const plotHeight = CHART_HEIGHT - PLOT.top - PLOT.bottom;

  return {
    minimum: low,
    maximum: high,
    y: (value) => PLOT.top + ((high - value) / (high - low)) * plotHeight,
  };
}

function linePath(
  points: TrendPoint[],
  valueForPoint: (point: TrendPoint) => number | null,
  x: (index: number) => number,
  y: (value: number) => number,
): string {
  return points
    .map((point, index) => {
      const value = valueForPoint(point);
      if (value === null) {
        return "";
      }
      return `${index === 0 ? "M" : "L"} ${x(index)} ${y(value)}`;
    })
    .filter(Boolean)
    .join(" ");
}

function combinedTrendObservations(point: TrendPoint): number {
  return (
    Math.max(0, point.treatment_observations) +
    Math.max(0, point.control_observations)
  );
}

function combinedTrendValue(point: TrendPoint): number | null {
  const series = [
    {
      value: point.treatment_value,
      observations: Math.max(0, point.treatment_observations),
    },
    {
      value: point.control_value,
      observations: Math.max(0, point.control_observations),
    },
  ].filter(
    (item): item is { value: number; observations: number } =>
      item.value !== null,
  );

  if (series.length === 0) {
    return null;
  }

  const observations = series.reduce(
    (total, item) => total + item.observations,
    0,
  );

  if (observations > 0) {
    return (
      series.reduce(
        (total, item) => total + item.value * item.observations,
        0,
      ) / observations
    );
  }

  return series.reduce((total, item) => total + item.value, 0) / series.length;
}

function downloadChart(svg: SVGSVGElement | null, filename: string): void {
  if (!svg) {
    return;
  }

  const source = new XMLSerializer().serializeToString(svg);
  const blob = new Blob([source], {
    type: "image/svg+xml;charset=utf-8",
  });
  const objectUrl = URL.createObjectURL(blob);
  const image = new Image();

  image.onload = () => {
    const scale = 2;
    const canvas = document.createElement("canvas");
    canvas.width = CHART_WIDTH * scale;
    canvas.height = CHART_HEIGHT * scale;
    const context = canvas.getContext("2d");

    if (!context) {
      URL.revokeObjectURL(objectUrl);
      return;
    }

    context.scale(scale, scale);
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, CHART_WIDTH, CHART_HEIGHT);
    context.drawImage(image, 0, 0, CHART_WIDTH, CHART_HEIGHT);
    URL.revokeObjectURL(objectUrl);

    canvas.toBlob((png) => {
      if (!png) {
        return;
      }
      const link = document.createElement("a");
      link.href = URL.createObjectURL(png);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    }, "image/png");
  };

  image.src = objectUrl;
}

type TrendFrequency = "daily" | "weekly";

function humanizeColumn(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function weightedAverage(
  numerator: number,
  denominator: number,
): number | null {
  return denominator > 0 ? numerator / denominator : null;
}

function weekStart(value: string): string {
  const parsed = new Date(`${value}T00:00:00`);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  const day = parsed.getUTCDay();
  const distance = day === 0 ? 6 : day - 1;

  parsed.setUTCDate(parsed.getUTCDate() - distance);

  return parsed.toISOString().slice(0, 10);
}

function aggregateTrend(
  data: DatasetVisualizations["trend"],
  frequency: TrendFrequency,
): DatasetVisualizations["trend"] {
  if (frequency === "daily") {
    return data;
  }

  const buckets = new Map<
    string,
    {
      treatmentNumerator: number;
      treatmentObservations: number;
      controlNumerator: number;
      controlObservations: number;
      phase: "pre" | "post";
    }
  >();

  for (const point of data) {
    const period = weekStart(point.period);
    const bucket = buckets.get(period) ?? {
      treatmentNumerator: 0,
      treatmentObservations: 0,
      controlNumerator: 0,
      controlObservations: 0,
      phase: point.phase,
    };

    if (point.phase === "post") {
      bucket.phase = "post";
    }

    if (point.treatment_value !== null && point.treatment_observations > 0) {
      bucket.treatmentNumerator +=
        point.treatment_value * point.treatment_observations;

      bucket.treatmentObservations += point.treatment_observations;
    }

    if (point.control_value !== null && point.control_observations > 0) {
      bucket.controlNumerator +=
        point.control_value * point.control_observations;

      bucket.controlObservations += point.control_observations;
    }

    buckets.set(period, bucket);
  }

  return [...buckets.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([period, bucket]) => ({
      period,
      treatment_value: weightedAverage(
        bucket.treatmentNumerator,
        bucket.treatmentObservations,
      ),
      control_value: weightedAverage(
        bucket.controlNumerator,
        bucket.controlObservations,
      ),
      treatment_observations: bucket.treatmentObservations,
      control_observations: bucket.controlObservations,
      phase: bucket.phase,
    }));
}

function averageTrendValue(
  data: DatasetVisualizations["trend"],
  key: "treatment_value" | "control_value",
): number | null {
  const values = data
    .map((point) => point[key])
    .filter((value): value is number => typeof value === "number");

  if (values.length === 0) {
    return null;
  }

  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function ExplorerVisualizations({
  visualizations,
  columns,
  activeTab,
  onTabChange,
  estimator = "difference_in_differences",
  onEstimatorChange,
  selectedOutcome,
  selectedInterventionDate,
  onInterventionDateChange,
  onOutcomeChange,
  onFilterMissing,
}: {
  visualizations: DatasetVisualizations;
  columns: ColumnSummary[];
  activeTab: VisualizationTab;
  onTabChange: (tab: VisualizationTab) => void;
  estimator?: string;
  onEstimatorChange?: (value: string) => void;
  selectedOutcome?: string;
  selectedInterventionDate?: string;
  onInterventionDateChange?: (value: string) => void;
  onOutcomeChange?: (column: string) => void;
  onFilterMissing?: (column: string) => void;
}) {
  const chartRef = useRef<SVGSVGElement>(null);
  const [breakdownColumn, setBreakdownColumn] = useState(
    Object.keys(visualizations.breakdowns)[0] ?? "",
  );
  const [frequency, setFrequency] = useState<TrendFrequency>("weekly");
  const [inspectedTrendPoint, setInspectedTrendPoint] =
    useState<TrendPoint | null>(null);
  const usesInterventionDate = estimator !== "marketing_mix_model";
  const usesSingleOutcomeSeries = estimator === "marketing_mix_model";

  const inferredInterventionDate =
    visualizations.trend.find((point) => point.phase === "post")?.period ?? "";

  const explicitInterventionDate = selectedInterventionDate ?? "";

  const detectedInterventionDate =
    visualizations.treatment_start_date || inferredInterventionDate;

  const resolvedInterventionDate = usesInterventionDate
    ? explicitInterventionDate || detectedInterventionDate
    : "";

  const interventionInputRef = useRef<HTMLInputElement>(null);
  const interventionEditingRef = useRef(false);
  const lastCommittedInterventionDateRef = useRef(explicitInterventionDate);
  const [interventionDateError, setInterventionDateError] = useState<
    string | null
  >(null);

  const minimumInterventionDate = visualizations.trend[0]?.period;
  const maximumInterventionDate =
    visualizations.trend[visualizations.trend.length - 1]?.period;

  useEffect(() => {
    lastCommittedInterventionDateRef.current = explicitInterventionDate;

    if (!interventionEditingRef.current && interventionInputRef.current) {
      interventionInputRef.current.value = explicitInterventionDate;
      setInterventionDateError(null);
    }
  }, [explicitInterventionDate]);

  const isCompleteValidInterventionDate = (
    input: HTMLInputElement,
  ): boolean =>
    /^\d{4}-\d{2}-\d{2}$/.test(input.value) &&
    input.valueAsDate !== null &&
    input.validity.valid;

  const interventionRangeMessage =
    minimumInterventionDate && maximumInterventionDate
      ? `Choose a date between ${date(minimumInterventionDate)} and ${date(maximumInterventionDate)}.`
      : "Choose a complete valid date.";

  const commitInterventionDate = (
    input: HTMLInputElement,
    allowEmpty: boolean,
  ) => {
    const value = input.value;

    if (value === "") {
      if (!allowEmpty || input.validity.badInput) {
        return;
      }
    } else if (!isCompleteValidInterventionDate(input)) {
      setInterventionDateError(interventionRangeMessage);
      return;
    }

    setInterventionDateError(null);

    if (value !== lastCommittedInterventionDateRef.current) {
      lastCommittedInterventionDateRef.current = value;
      onInterventionDateChange?.(value);
    }
  };

  const numericColumns = columns.filter((column) =>
    ["integer", "float"].includes(column.inferred_type),
  );

  const hasMappedOutcome = Boolean(visualizations.outcome_column);

  const outcomeValue = hasMappedOutcome
    ? selectedOutcome || visualizations.outcome_column || ""
    : "";

  const displayedTrend = aggregateTrend(visualizations.trend, frequency);

  const preTreatmentTrend = resolvedInterventionDate
    ? displayedTrend.filter((point) => point.phase === "pre")
    : [];

  const postTreatmentTrend = resolvedInterventionDate
    ? displayedTrend.filter((point) => point.phase === "post")
    : [];

  const preTreatmentAverage = averageTrendValue(
    preTreatmentTrend,
    "treatment_value",
  );

  const postTreatmentAverage = averageTrendValue(
    postTreatmentTrend,
    "treatment_value",
  );
  const tabs: {
    id: VisualizationTab;
    label: string;
  }[] = [
    { id: "trend", label: "Trend" },
    { id: "distribution", label: "Distribution" },
    { id: "missingness", label: "Missingness" },
    { id: "breakdown", label: "Breakdown" },
  ];
  const selectedBreakdown = visualizations.breakdowns[breakdownColumn] ?? [];

  return (
    <section
      className="explorer-evidence"
      aria-labelledby="explorer-evidence-heading"
    >
      <header className="explorer-section-heading">
        <div>
          <h2 id="explorer-evidence-heading">Understand the evidence</h2>
          <p>
            Compare groups, inspect the outcome shape, and find rows that need
            attention before analysis.
          </p>
        </div>

        <div className="explorer-evidence-controls">
          <label className="explorer-inline-select">
            <span>Method</span>
            <select
              aria-label="Causal method"
              value={estimator}
              onChange={(event) => onEstimatorChange?.(event.target.value)}
            >
              <option value="difference_in_differences">
                Difference in Differences
              </option>
              <option value="synthetic_control">Synthetic Control</option>
              <option value="geo_holdout">Geo Holdout</option>
              <option value="marketing_mix_model">
                Marketing Mix Modeling
              </option>
              <option value="off_policy_evaluation">
                Off-Policy Evaluation
              </option>
            </select>
          </label>

          {numericColumns.length > 0 ? (
            <label className="explorer-inline-select">
              <span>Outcome</span>
              <select
                aria-label="Outcome"
                value={outcomeValue}
                disabled={!hasMappedOutcome}
                onChange={(event) => onOutcomeChange?.(event.target.value)}
              >
                {!hasMappedOutcome ? (
                  <option value="">Map an outcome first</option>
                ) : null}

                {numericColumns.map((column) => (
                  <option key={column.name} value={column.name}>
                    {humanizeColumn(column.name)}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {usesInterventionDate ? (
            <div className="explorer-inline-select explorer-intervention-control">
              <label htmlFor="explorer-intervention-date">Intervention</label>
              <input
                id="explorer-intervention-date"
                ref={interventionInputRef}
                aria-label="Intervention date"
                aria-describedby={
                  [
                    interventionDateError ? "intervention-date-error" : "",
                    !explicitInterventionDate && detectedInterventionDate
                      ? "detected-intervention-date"
                      : "",
                  ]
                    .filter(Boolean)
                    .join(" ") || undefined
                }
                aria-invalid={Boolean(interventionDateError)}
                type="date"
                defaultValue={explicitInterventionDate}
                min={minimumInterventionDate}
                max={maximumInterventionDate}
                onFocus={() => {
                  interventionEditingRef.current = true;
                }}
                onChange={(event) => {
                  if (event.currentTarget.value === "") {
                    setInterventionDateError(null);
                    return;
                  }

                  commitInterventionDate(event.currentTarget, false);
                }}
                onBlur={(event) => {
                  interventionEditingRef.current = false;
                  commitInterventionDate(event.currentTarget, true);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.currentTarget.blur();
                  }
                }}
              />
              {interventionDateError ? (
                <small id="intervention-date-error" role="alert">
                  {interventionDateError}
                </small>
              ) : null}
              {!explicitInterventionDate && detectedInterventionDate ? (
                <div
                  className="explorer-detected-intervention"
                  id="detected-intervention-date"
                >
                  <span>
                    Detected from dataset: {date(detectedInterventionDate)}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      lastCommittedInterventionDateRef.current =
                        detectedInterventionDate;
                      onInterventionDateChange?.(detectedInterventionDate);
                    }}
                  >
                    Use detected date
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}

          <label className="explorer-inline-select">
            <span>Frequency</span>
            <select
              aria-label="Frequency"
              value={frequency}
              onChange={(event) =>
                setFrequency(event.target.value as TrendFrequency)
              }
            >
              <option value="weekly">Weekly</option>
              <option value="daily">Daily</option>
            </select>
          </label>
        </div>
      </header>

      <section
        className="explorer-evidence-kpis"
        aria-label="Selected evidence summary"
      >
        <article>
          <span>Selected outcome</span>
          <strong>
            {outcomeValue ? humanizeColumn(outcomeValue) : "Not mapped"}
          </strong>
          <small>
            {hasMappedOutcome
              ? "From the backend dataset mapping"
              : "Complete semantic mapping to unlock treatment-period insights."}
          </small>
        </article>

        {usesInterventionDate ? (
          <>
            <article>
              <span>
                {explicitInterventionDate
                  ? "Selected intervention date"
                  : detectedInterventionDate
                    ? "Detected intervention date"
                    : "Intervention date"}
              </span>
              <strong>
                {resolvedInterventionDate
                  ? date(resolvedInterventionDate)
                  : "Not detected"}
              </strong>
              <small>
                {explicitInterventionDate
                  ? "Explicit date applied to Explorer requests"
                  : detectedInterventionDate
                    ? "Detected from the treatment transition; not applied as an explicit filter"
                    : "Enter the known beginning of the post-treatment period"}
              </small>
            </article>

            <article>
              <span>Pre-treatment</span>
              <strong>
                {preTreatmentAverage === null
                  ? "—"
                  : number(preTreatmentAverage)}
              </strong>
              <small>Average treatment-group outcome</small>
            </article>

            <article>
              <span>Post-treatment</span>
              <strong>
                {postTreatmentAverage === null
                  ? "—"
                  : number(postTreatmentAverage)}
              </strong>
              <small>Average treatment-group outcome</small>
            </article>
          </>
        ) : (
          <>
            <article>
              <span>Dataset start</span>
              <strong>
                {displayedTrend[0]?.period
                  ? date(displayedTrend[0].period)
                  : "Not available"}
              </strong>
              <small>First observed period in this dataset</small>
            </article>

            <article>
              <span>Dataset end</span>
              <strong>
                {displayedTrend[displayedTrend.length - 1]?.period
                  ? date(displayedTrend[displayedTrend.length - 1].period)
                  : "Not available"}
              </strong>
              <small>Last observed period in this dataset</small>
            </article>

            <article>
              <span>Observed periods</span>
              <strong>{displayedTrend.length.toLocaleString("en-US")}</strong>
              <small>Use analysis dates later during configuration</small>
            </article>
          </>
        )}
      </section>

      {inspectedTrendPoint ? (
        <section
          className="explorer-inspection-kpis"
          aria-label="Selected chart period"
          data-single-series={usesSingleOutcomeSeries || undefined}
        >
          <article>
            <span>Selected period</span>
            <strong>{date(inspectedTrendPoint.period)}</strong>
            <small>Hovering or pinned chart period</small>
          </article>

          {usesSingleOutcomeSeries ? (
            <>
              <article>
                <span>Outcome</span>
                <strong>{number(combinedTrendValue(inspectedTrendPoint))}</strong>
                <small>Average across all observations</small>
              </article>

              <article>
                <span>Observations</span>
                <strong>
                  {new Intl.NumberFormat("en-US").format(
                    combinedTrendObservations(inspectedTrendPoint),
                  )}
                </strong>
                <small>Rows represented in this period</small>
              </article>
            </>
          ) : (
            <>
              <article>
                <span>Treatment</span>
                <strong>{number(inspectedTrendPoint.treatment_value)}</strong>
                <small>
                  {new Intl.NumberFormat("en-US").format(
                    inspectedTrendPoint.treatment_observations,
                  )}{" "}
                  observations
                </small>
              </article>

              <article>
                <span>Control</span>
                <strong>{number(inspectedTrendPoint.control_value)}</strong>
                <small>
                  {new Intl.NumberFormat("en-US").format(
                    inspectedTrendPoint.control_observations,
                  )}{" "}
                  observations
                </small>
              </article>

              <article>
                <span>Difference</span>
                <strong>
                  {signedNumber(
                    inspectedTrendPoint.treatment_value !== null &&
                      inspectedTrendPoint.control_value !== null
                      ? inspectedTrendPoint.treatment_value -
                          inspectedTrendPoint.control_value
                      : null,
                  )}
                </strong>
                <small>Treatment minus control</small>
              </article>
            </>
          )}
        </section>
      ) : null}

      <div className="explorer-tabbar">
        <div
          className="explorer-tabs"
          role="tablist"
          aria-label="Dataset visualizations"
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              id={`explorer-tab-${tab.id}`}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`explorer-panel-${tab.id}`}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <button
          className="explorer-chart-download"
          type="button"
          onClick={() =>
            downloadChart(chartRef.current, `dataset-${activeTab}.png`)
          }
        >
          <DownloadSimpleIcon size={17} aria-hidden="true" />
          Download chart as PNG
        </button>
      </div>
      {activeTab === "trend" && resolvedInterventionDate ? (
        <div className="explorer-phase-context" aria-label="Treatment periods">
          <span>Pre-treatment period</span>
          <span>Post-treatment period</span>
        </div>
      ) : null}

      <div
        id={`explorer-panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`explorer-tab-${activeTab}`}
        className="explorer-chart-panel"
      >
        {activeTab === "trend" ? (
          <TrendChart
            ref={chartRef}
            data={displayedTrend}
            outcome={outcomeValue || visualizations.outcome_column}
            treatmentStart={resolvedInterventionDate || null}
            singleOutcomeSeries={usesSingleOutcomeSeries}
            onInspect={setInspectedTrendPoint}
          />
        ) : null}

        {activeTab === "distribution" ? (
          <DistributionChart
            ref={chartRef}
            data={visualizations.distribution.bins}
            outcome={visualizations.outcome_column}
            distribution={visualizations.distribution}
          />
        ) : null}

        {activeTab === "missingness" ? (
          <MissingnessChart
            ref={chartRef}
            data={visualizations.missingness}
            onFilterMissing={onFilterMissing}
          />
        ) : null}

        {activeTab === "breakdown" ? (
          <BreakdownChart
            ref={chartRef}
            data={selectedBreakdown}
            columns={Object.keys(visualizations.breakdowns)}
            selectedColumn={breakdownColumn}
            outcome={visualizations.outcome_column}
            onColumnChange={setBreakdownColumn}
          />
        ) : null}
      </div>

      {visualizations.balance && !usesSingleOutcomeSeries ? (
        <BalanceSummary balance={visualizations.balance} />
      ) : null}
    </section>
  );
}

const TrendChart = forwardRef<
  SVGSVGElement,
  {
    data: TrendPoint[];
    outcome: string | null;
    treatmentStart: string | null;
    singleOutcomeSeries?: boolean;
    onInspect?: (point: TrendPoint | null) => void;
  }
>(function TrendChart(
  { data, outcome, treatmentStart, singleOutcomeSeries = false, onInspect },
  ref,
) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const [pinnedIndex, setPinnedIndex] = useState<number | null>(null);

  const values = singleOutcomeSeries
    ? data
        .map(combinedTrendValue)
        .filter((value): value is number => value !== null)
    : data.flatMap((point) =>
        [point.treatment_value, point.control_value].filter(
          (value): value is number => value !== null,
        ),
      );

  if (data.length === 0 || values.length === 0) {
    return (
      <ChartEmpty>
        {singleOutcomeSeries
          ? "Map a time and numeric outcome column to see the outcome trend."
          : "Map a time, treatment, and numeric outcome column to see the group trend."}
      </ChartEmpty>
    );
  }

  const scale = chartScale(values);

  const plotWidth = CHART_WIDTH - PLOT.left - PLOT.right;

  const plotHeight = CHART_HEIGHT - PLOT.top - PLOT.bottom;

  const x = (index: number) =>
    PLOT.left +
    (data.length === 1
      ? plotWidth / 2
      : (index / (data.length - 1)) * plotWidth);

  const markerIndex = treatmentStart
    ? data.findIndex((point) => point.period >= treatmentStart)
    : -1;

  const markerX = markerIndex >= 0 ? x(markerIndex) : null;

  const tickStep = Math.max(1, Math.ceil(data.length / 7));

  const selectedIndex = pinnedIndex ?? hoveredIndex;

  const selectedPoint =
    selectedIndex === null ? null : (data[selectedIndex] ?? null);

  const selectedDifference =
    selectedPoint?.treatment_value !== null &&
    selectedPoint?.treatment_value !== undefined &&
    selectedPoint.control_value !== null &&
    selectedPoint.control_value !== undefined
      ? selectedPoint.treatment_value - selectedPoint.control_value
      : null;

  const selectedObservations = selectedPoint
    ? combinedTrendObservations(selectedPoint)
    : 0;

  const selectedOutcome = selectedPoint
    ? combinedTrendValue(selectedPoint)
    : null;

  const tooltipAlignment =
    selectedIndex === null
      ? "center"
      : selectedIndex < data.length / 3
        ? "start"
        : selectedIndex > (data.length * 2) / 3
          ? "end"
          : "center";

  const clearSelection = () => {
    setHoveredIndex(null);
    setPinnedIndex(null);
    onInspect?.(null);
  };

  const inspectIndex = (index: number) => {
    if (pinnedIndex !== null) {
      return;
    }

    setHoveredIndex(index);
    onInspect?.(data[index] ?? null);
  };

  const togglePinnedIndex = (index: number) => {
    if (pinnedIndex === index) {
      clearSelection();
      return;
    }

    setPinnedIndex(index);
    setHoveredIndex(index);
    onInspect?.(data[index] ?? null);
  };

  return (
    <div
      className="explorer-chart-with-context"
      role="group"
      aria-label="Interactive trend chart"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          clearSelection();
        }
      }}
    >
      <div className="explorer-chart-copy">
        <div>
          <strong>
            {outcome ? `${label(outcome)} over time` : "Outcome over time"}
          </strong>

          <span>Hover to inspect. Click a period to pin its values.</span>
        </div>

        {!singleOutcomeSeries ? (
          <div className="explorer-chart-legend">
            <span data-series="treatment">Treatment</span>

            <span data-series="control">Control</span>
          </div>
        ) : null}
      </div>

      {treatmentStart ? (
        <p className="explorer-treatment-note">
          Treatment begins {date(treatmentStart)}
        </p>
      ) : null}

      <svg
        ref={ref}
        className="explorer-svg-chart"
        role="img"
        aria-label={`${outcome ? label(outcome) : "Outcome"} outcome trend`}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        onMouseLeave={() => {
          if (pinnedIndex === null) {
            setHoveredIndex(null);
            onInspect?.(null);
          }
        }}
        onClick={(event) => {
          const target = event.target as Element;

          if (!target.closest('[data-chart-inspection-target="true"]')) {
            clearSelection();
          }
        }}
      >
        {markerX !== null ? (
          <>
            <rect
              className="explorer-chart-pre"
              x={PLOT.left}
              y={PLOT.top}
              width={Math.max(0, markerX - PLOT.left)}
              height={plotHeight}
            />

            <rect
              data-testid="post-treatment-region"
              className="explorer-chart-post"
              x={markerX}
              y={PLOT.top}
              width={CHART_WIDTH - PLOT.right - markerX}
              height={plotHeight}
            />
          </>
        ) : null}

        {[0, 1, 2, 3].map((index) => {
          const ratio = index / 3;

          const chartY = PLOT.top + ratio * plotHeight;

          const value = scale.maximum - ratio * (scale.maximum - scale.minimum);

          return (
            <g key={index}>
              <line
                className="explorer-chart-grid"
                x1={PLOT.left}
                x2={CHART_WIDTH - PLOT.right}
                y1={chartY}
                y2={chartY}
              />

              <text
                className="explorer-axis-label"
                x={PLOT.left - 10}
                y={chartY + 4}
                textAnchor="end"
              >
                {number(value)}
              </text>
            </g>
          );
        })}

        {markerX !== null ? (
          <line
            className="explorer-treatment-marker"
            x1={markerX}
            x2={markerX}
            y1={PLOT.top}
            y2={CHART_HEIGHT - PLOT.bottom}
          />
        ) : null}

        {singleOutcomeSeries ? (
          <path
            className="explorer-series-outcome"
            d={linePath(data, combinedTrendValue, x, scale.y)}
          />
        ) : (
          <>
            <path
              className="explorer-series-treatment"
              d={linePath(
                data,
                (point) => point.treatment_value,
                x,
                scale.y,
              )}
            />

            <path
              className="explorer-series-control"
              d={linePath(data, (point) => point.control_value, x, scale.y)}
            />
          </>
        )}

        {data.flatMap((point, index) => {
          const series = singleOutcomeSeries
            ? [
                {
                  key: "outcome",
                  label: "Outcome",
                  value: combinedTrendValue(point),
                  observations: combinedTrendObservations(point),
                },
              ]
            : [
                {
                  key: "treatment",
                  label: "Treatment",
                  value: point.treatment_value,
                  observations: point.treatment_observations,
                },
                {
                  key: "control",
                  label: "Control",
                  value: point.control_value,
                  observations: point.control_observations,
                },
              ];

          return series.flatMap((item) =>
            item.value === null
              ? []
              : [
                  <circle
                    key={`${point.period}-${item.key}`}
                    className={`explorer-point-${item.key}`}
                    cx={x(index)}
                    cy={scale.y(item.value)}
                    r={4}
                  >
                    <title>
                      {date(point.period)},{" "}
                      {item.label}:{" "}
                      {number(item.value)} from {item.observations} observations
                    </title>
                  </circle>,
                ],
          );
        })}

        {data.map((point, index) => {
          const step =
            data.length > 1 ? plotWidth / (data.length - 1) : plotWidth;

          const left = index === 0 ? PLOT.left : x(index) - step / 2;

          const right =
            index === data.length - 1
              ? CHART_WIDTH - PLOT.right
              : x(index) + step / 2;

          return (
            <rect
              key={`inspect-${point.period}`}
              className="explorer-chart-hit-target"
              data-chart-inspection-target="true"
              role="button"
              tabIndex={0}
              aria-pressed={pinnedIndex === index}
              aria-label={[
                `Inspect ${date(point.period)}`,
                ...(singleOutcomeSeries
                  ? [
                      combinedTrendValue(point) === null
                        ? "Outcome unavailable"
                        : `Outcome ${number(combinedTrendValue(point))}`,
                    ]
                  : [
                      point.treatment_value === null
                        ? "Treatment unavailable"
                        : `Treatment ${number(point.treatment_value)}`,
                      point.control_value === null
                        ? "Control unavailable"
                        : `Control ${number(point.control_value)}`,
                    ]),
              ].join(". ")}
              x={left}
              y={PLOT.top}
              width={right - left}
              height={plotHeight}
              onMouseEnter={() => inspectIndex(index)}
              onFocus={() => inspectIndex(index)}
              onBlur={() => {
                if (pinnedIndex === null) {
                  setHoveredIndex(null);
                  onInspect?.(null);
                }
              }}
              onClick={(event) => {
                event.stopPropagation();
                togglePinnedIndex(index);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  togglePinnedIndex(index);
                }
              }}
            />
          );
        })}

        {selectedPoint && selectedIndex !== null ? (
          <>
            <line
              className="explorer-chart-crosshair"
              x1={x(selectedIndex)}
              x2={x(selectedIndex)}
              y1={PLOT.top}
              y2={CHART_HEIGHT - PLOT.bottom}
            />

            {singleOutcomeSeries && selectedOutcome !== null ? (
              <circle
                className="explorer-chart-selected-ring explorer-chart-selected-outcome"
                cx={x(selectedIndex)}
                cy={scale.y(selectedOutcome)}
                r={7}
              />
            ) : null}

            {!singleOutcomeSeries ? (
              <>
                {selectedPoint.treatment_value !== null ? (
                  <circle
                    className="explorer-chart-selected-ring explorer-chart-selected-treatment"
                    cx={x(selectedIndex)}
                    cy={scale.y(selectedPoint.treatment_value)}
                    r={7}
                  />
                ) : null}

                {selectedPoint.control_value !== null ? (
                  <circle
                    className="explorer-chart-selected-ring explorer-chart-selected-control"
                    cx={x(selectedIndex)}
                    cy={scale.y(selectedPoint.control_value)}
                    r={7}
                  />
                ) : null}
              </>
            ) : null}
          </>
        ) : null}

        {data.map((point, index) => {
          const shouldShow =
            index === 0 || index === data.length - 1 || index % tickStep === 0;

          if (!shouldShow) {
            return null;
          }

          return (
            <text
              key={point.period}
              className="explorer-axis-label explorer-axis-date"
              x={x(index)}
              y={CHART_HEIGHT - 15}
              textAnchor="middle"
            >
              {new Intl.DateTimeFormat("en-US", {
                month: "short",
                year: "2-digit",
                timeZone: "UTC",
              }).format(new Date(`${point.period.slice(0, 10)}T00:00:00Z`))}
            </text>
          );
        })}
      </svg>

      {selectedPoint && selectedIndex !== null ? (
        <div
          className="explorer-chart-tooltip"
          data-align={tooltipAlignment}
          data-pinned={pinnedIndex !== null}
          role="status"
          aria-label="Chart period details"
          style={{
            left: `${(x(selectedIndex) / CHART_WIDTH) * 100}%`,
          }}
        >
          <header>
            <strong>{date(selectedPoint.period)}</strong>

            <span>{pinnedIndex !== null ? "Pinned" : "Hovering"}</span>
          </header>

          <dl>
            {singleOutcomeSeries ? (
              <div>
                <dt>Outcome</dt>
                <dd>{number(selectedOutcome)}</dd>
              </div>
            ) : (
              <>
                <div>
                  <dt>Treatment</dt>
                  <dd>{number(selectedPoint.treatment_value)}</dd>
                </div>

                <div>
                  <dt>Control</dt>
                  <dd>{number(selectedPoint.control_value)}</dd>
                </div>

                <div>
                  <dt>Difference</dt>
                  <dd>{signedNumber(selectedDifference)}</dd>
                </div>
              </>
            )}

            <div>
              <dt>Observations</dt>
              <dd>
                {new Intl.NumberFormat("en-US").format(selectedObservations)}
              </dd>
            </div>
          </dl>

          <small>
            {pinnedIndex !== null
              ? "Press Escape or click the chart background to clear."
              : "Click to pin this period."}
          </small>
        </div>
      ) : null}
    </div>
  );
});

const DistributionChart = forwardRef<
  SVGSVGElement,
  {
    data: HistogramBin[];
    outcome: string | null;
    distribution: OutcomeDistribution;
  }
>(function DistributionChart({ data, outcome, distribution }, ref) {
  const maximum = Math.max(
    1,
    ...data.map((item) => item.treatment_count + item.control_count),
  );
  const plotWidth = CHART_WIDTH - PLOT.left - PLOT.right;
  const barWidth = data.length ? plotWidth / data.length : plotWidth;
  const plotHeight = CHART_HEIGHT - PLOT.top - PLOT.bottom;

  return (
    <div className="explorer-chart-with-context">
      <div className="explorer-chart-copy">
        <div>
          <strong>
            {outcome
              ? `${label(outcome)} distribution`
              : "Outcome distribution"}
          </strong>
          <span>Treatment and control observations by range</span>
        </div>
        <div className="explorer-chart-legend">
          <span data-series="treatment">Treatment</span>
          <span data-series="control">Control</span>
        </div>
      </div>

      <svg
        ref={ref}
        className="explorer-svg-chart"
        role="img"
        aria-label={`${
          outcome ? label(outcome) : "Outcome"
        } distribution histogram`}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      >
        {data.map((item, index) => {
          const treatmentHeight = (item.treatment_count / maximum) * plotHeight;
          const controlHeight = (item.control_count / maximum) * plotHeight;
          const baseX = PLOT.left + index * barWidth;
          return (
            <g key={`${item.minimum}-${item.maximum}`}>
              <rect
                className="explorer-histogram-treatment"
                x={baseX + barWidth * 0.12}
                y={CHART_HEIGHT - PLOT.bottom - treatmentHeight}
                width={barWidth * 0.35}
                height={treatmentHeight}
              >
                <title>
                  Treatment: {item.treatment_count} observations from{" "}
                  {number(item.minimum)} to {number(item.maximum)}
                </title>
              </rect>
              <rect
                className="explorer-histogram-control"
                x={baseX + barWidth * 0.51}
                y={CHART_HEIGHT - PLOT.bottom - controlHeight}
                width={barWidth * 0.35}
                height={controlHeight}
              >
                <title>
                  Control: {item.control_count} observations from{" "}
                  {number(item.minimum)} to {number(item.maximum)}
                </title>
              </rect>
            </g>
          );
        })}
      </svg>

      <dl className="explorer-stat-list">
        <div>
          <dt>Median</dt>
          <dd>{number(distribution.median)}</dd>
        </div>
        <div>
          <dt>First quartile</dt>
          <dd>{number(distribution.first_quartile)}</dd>
        </div>
        <div>
          <dt>Third quartile</dt>
          <dd>{number(distribution.third_quartile)}</dd>
        </div>
        <div>
          <dt>Possible outliers</dt>
          <dd>{number(distribution.outlier_count)}</dd>
        </div>
        <div>
          <dt>Sample size</dt>
          <dd>{distribution.sample_size} observations</dd>
        </div>
      </dl>
    </div>
  );
});

const MissingnessChart = forwardRef<
  SVGSVGElement,
  {
    data: MissingnessPoint[];
    onFilterMissing?: (column: string) => void;
  }
>(function MissingnessChart({ data, onFilterMissing }, ref) {
  const sorted = useMemo(
    () =>
      [...data].sort(
        (left, right) => right.missing_percentage - left.missing_percentage,
      ),
    [data],
  );
  const visible = sorted.slice(0, 12);
  const rowHeight = 28;
  const height = Math.max(180, visible.length * rowHeight + 48);

  return (
    <div className="explorer-chart-with-context">
      <div className="explorer-chart-copy">
        <div>
          <strong>Missing values by column</strong>
          <span>Select an affected column to inspect its missing rows</span>
        </div>
      </div>

      <svg
        ref={ref}
        className="explorer-svg-chart explorer-missingness-svg"
        role="img"
        aria-label="Missing value percentage by column"
        viewBox={`0 0 ${CHART_WIDTH} ${height}`}
      >
        {visible.map((item, index) => {
          const y = 24 + index * rowHeight;
          const width = (item.missing_percentage / 100) * 480;
          return (
            <g key={item.column}>
              <text className="explorer-missing-label" x={PLOT.left} y={y + 13}>
                {item.column}
              </text>
              <rect
                className="explorer-missing-track"
                x={220}
                y={y}
                width={480}
                height={14}
                rx={7}
              />
              <rect
                className="explorer-missing-fill"
                x={220}
                y={y}
                width={Math.max(item.missing_percentage > 0 ? 2 : 0, width)}
                height={14}
                rx={7}
              >
                <title>
                  {item.column}: {number(item.missing_percentage)}% missing,{" "}
                  {item.missing_count} rows
                </title>
              </rect>
              <text
                className="explorer-missing-value"
                x={716}
                y={y + 12}
                textAnchor="end"
              >
                {number(item.missing_percentage)}%
              </text>
            </g>
          );
        })}
      </svg>

      <div className="explorer-missing-actions">
        {visible
          .filter((item) => item.missing_count > 0)
          .map((item) => (
            <button
              key={item.column}
              type="button"
              onClick={() => onFilterMissing?.(item.column)}
            >
              Filter to {item.missing_count} rows missing {item.column}
            </button>
          ))}
      </div>
    </div>
  );
});

const BreakdownChart = forwardRef<
  SVGSVGElement,
  {
    data: BreakdownPoint[];
    columns: string[];
    selectedColumn: string;
    outcome: string | null;
    onColumnChange: (column: string) => void;
  }
>(function BreakdownChart(
  { data, columns, selectedColumn, outcome, onColumnChange },
  ref,
) {
  const maximum = Math.max(1, ...data.map((item) => item.outcome_mean ?? 0));
  const visible = data.slice(0, 10);
  const rowHeight = 30;
  const height = Math.max(190, visible.length * rowHeight + 50);

  if (columns.length === 0) {
    return (
      <ChartEmpty>
        Add a categorical market, region, or channel column to compare groups.
      </ChartEmpty>
    );
  }

  return (
    <div className="explorer-chart-with-context">
      <div className="explorer-chart-copy">
        <div>
          <strong>
            {outcome ?? "Outcome"} by {selectedColumn}
          </strong>
          <span>
            Mean outcome with treatment and control observation counts
          </span>
        </div>
        <label className="explorer-inline-select">
          <span>Breakdown</span>
          <select
            aria-label="Break down outcome by"
            value={selectedColumn}
            onChange={(event) => onColumnChange(event.target.value)}
          >
            {columns.map((column) => (
              <option key={column} value={column}>
                {column}
              </option>
            ))}
          </select>
        </label>
      </div>

      <svg
        ref={ref}
        className="explorer-svg-chart"
        role="img"
        aria-label={`${outcome ?? "Outcome"} by ${selectedColumn}`}
        viewBox={`0 0 ${CHART_WIDTH} ${height}`}
      >
        {visible.map((item, index) => {
          const y = 24 + index * rowHeight;
          const width = ((item.outcome_mean ?? 0) / maximum) * 440;
          return (
            <g key={item.value}>
              <text className="explorer-missing-label" x={PLOT.left} y={y + 14}>
                {item.value}
              </text>
              <rect
                className="explorer-breakdown-bar"
                x={220}
                y={y}
                width={width}
                height={16}
                rx={4}
              >
                <title>
                  {item.value}: mean {number(item.outcome_mean)},{" "}
                  {item.observation_count} observations, {item.treatment_count}{" "}
                  treatment, {item.control_count} control
                </title>
              </rect>
              <text
                className="explorer-missing-value"
                x={690}
                y={y + 13}
                textAnchor="end"
              >
                {number(item.outcome_mean)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
});

function BalanceSummary({ balance }: { balance: TreatmentBalance }) {
  return (
    <section
      className="explorer-balance"
      aria-label="Treatment and control balance"
    >
      <div className="explorer-balance-heading">
        <div>
          <strong>Treatment and control balance</strong>
          <span>
            {balance.treatment_value} means treatment. {balance.control_value}{" "}
            means control.
          </span>
        </div>
        <span data-status={balance.status === "Balanced" ? "good" : "warning"}>
          {balance.status}
        </span>
      </div>

      <div className="explorer-balance-groups">
        <article>
          <span>{balance.control_label}</span>
          <strong>
            {number(balance.control_count)}
            <small>{number(balance.control_percentage)}%</small>
          </strong>
          <p>
            {balance.control_pre_count} pre, {balance.control_post_count} post
          </p>
        </article>
        <article>
          <span>{balance.treatment_label}</span>
          <strong>
            {number(balance.treatment_count)}
            <small>{number(balance.treatment_percentage)}%</small>
          </strong>
          <p>
            {balance.treatment_pre_count} pre, {balance.treatment_post_count}{" "}
            post
          </p>
        </article>
      </div>
    </section>
  );
}

function ChartEmpty({ children }: { children: ReactNode }) {
  return (
    <div className="explorer-chart-empty">
      <strong>This visualization needs more mapping</strong>
      <p>{children}</p>
    </div>
  );
}
