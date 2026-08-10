import type {
  DatasetPreview,
  GeographySummary,
} from "@/lib/data-products/types";

import { AnalysisGeographyMapLoader } from "./analysis-geography-map-loader";

import type {
  AnalysisEstimatorType,
  FilterOperator,
  FilterRule as RequestFilterRule,
  FilterValue,
} from "@/lib/analysis-configuration/request";

export type AnalysisFilterRule = RequestFilterRule & {
  id: string;
};

type FilterOperatorOption = {
  value: FilterOperator;
  label: string;
};

type AnalysisFiltersStepProps = {
  preview: DatasetPreview;
  geographySummary: GeographySummary;
  estimator: AnalysisEstimatorType;
  unitColumn: string;

  selectedFilterColumn: string;
  selectedFilterOperator: FilterOperator;
  filterValue: string;
  filterRules: AnalysisFilterRule[];

  selectedGeographies: string[];
  excludedGeographies: string[];

  segmentColumn: string;
  selectedSegments: string[];
  excludedSegments: string[];

  onFilterColumnChange: (
    columnName: string,
    defaultOperator: FilterOperator | null,
  ) => void;

  onFilterOperatorChange: (operator: FilterOperator) => void;

  onFilterValueChange: (value: string) => void;

  onAddFilter: (rule: AnalysisFilterRule) => void;

  onRemoveFilter: (ruleId: string) => void;

  onSelectedGeographyChange: (value: string, checked: boolean) => void;

  onExcludedGeographyChange: (value: string, checked: boolean) => void;

  onSegmentColumnChange: (value: string) => void;

  onSelectedSegmentChange: (value: string, checked: boolean) => void;

  onExcludedSegmentChange: (value: string, checked: boolean) => void;

  onContinue: () => void;
};

const EQUALITY_FILTER_OPERATORS: FilterOperatorOption[] = [
  {
    value: "equals",
    label: "Equals",
  },
  {
    value: "not_equals",
    label: "Not equals",
  },
];

const ORDERED_FILTER_OPERATORS: FilterOperatorOption[] = [
  {
    value: "greater_than",
    label: "Greater than",
  },
  {
    value: "greater_than_or_equal",
    label: "Greater than or equal",
  },
  {
    value: "less_than",
    label: "Less than",
  },
  {
    value: "less_than_or_equal",
    label: "Less than or equal",
  },
];

const NULL_FILTER_OPERATORS: FilterOperatorOption[] = [
  {
    value: "is_null",
    label: "Is null",
  },
  {
    value: "is_not_null",
    label: "Is not null",
  },
];

function filterOperatorsForType(inferredType: string): FilterOperatorOption[] {
  if (inferredType === "string") {
    return [
      ...EQUALITY_FILTER_OPERATORS,
      {
        value: "contains",
        label: "Contains",
      },
      ...NULL_FILTER_OPERATORS,
    ];
  }

  if (
    inferredType === "integer" ||
    inferredType === "float" ||
    inferredType === "date" ||
    inferredType === "datetime"
  ) {
    return [
      ...EQUALITY_FILTER_OPERATORS,
      ...ORDERED_FILTER_OPERATORS,
      ...NULL_FILTER_OPERATORS,
    ];
  }

  return [...EQUALITY_FILTER_OPERATORS, ...NULL_FILTER_OPERATORS];
}

function filterValueInputType(
  inferredType: string,
): "text" | "number" | "date" {
  if (inferredType === "integer" || inferredType === "float") {
    return "number";
  }

  if (inferredType === "date" || inferredType === "datetime") {
    return "date";
  }

  return "text";
}

function operatorRequiresValue(operator: FilterOperator): boolean {
  return operator !== "is_null" && operator !== "is_not_null";
}

function filterOperatorLabel(operator: FilterOperator): string {
  const options = [
    ...EQUALITY_FILTER_OPERATORS,
    ...ORDERED_FILTER_OPERATORS,
    ...NULL_FILTER_OPERATORS,
    {
      value: "contains" as const,
      label: "Contains",
    },
  ];

  return options.find((option) => option.value === operator)?.label ?? operator;
}

function typedFilterValue(inferredType: string, rawValue: string): FilterValue {
  if (inferredType === "integer" || inferredType === "float") {
    return {
      type: "number",
      value: Number(rawValue),
    };
  }

  if (inferredType === "date" || inferredType === "datetime") {
    return {
      type: "date",
      value: rawValue,
    };
  }

  if (inferredType === "boolean") {
    return {
      type: "boolean",
      value: rawValue.toLocaleLowerCase() === "true",
    };
  }

  return {
    type: "string",
    value: rawValue,
  };
}

function observedValues(
  rows: Array<Record<string, unknown>>,
  columnName: string,
): string[] {
  if (!columnName) {
    return [];
  }

  const values: string[] = [];

  const seen = new Set<string>();

  for (const row of rows) {
    const rawValue = row[columnName];

    if (rawValue === null || rawValue === undefined) {
      continue;
    }

    const value = String(rawValue).trim();

    if (value.length === 0 || seen.has(value)) {
      continue;
    }

    seen.add(value);

    values.push(value);
  }

  return values;
}

function formatPopulationMetric(value: number | null): string {
  if (value === null) {
    return "Unavailable";
  }

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
  }).format(value);
}

function humanizeMetricName(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function AnalysisFiltersStep({
  preview,
  geographySummary,
  estimator,
  unitColumn,
  selectedFilterColumn,
  selectedFilterOperator,
  filterValue,
  filterRules,
  selectedGeographies,
  excludedGeographies,
  segmentColumn,
  selectedSegments,
  excludedSegments,
  onFilterColumnChange,
  onFilterOperatorChange,
  onFilterValueChange,
  onAddFilter,
  onRemoveFilter,
  onSelectedGeographyChange,
  onExcludedGeographyChange,
  onSegmentColumnChange,
  onSelectedSegmentChange,
  onExcludedSegmentChange,
  onContinue,
}: AnalysisFiltersStepProps) {
  const coordinatesRelevant = estimator === "geo_holdout";
  const selectedColumn =
    preview.columns.find((column) => column.name === selectedFilterColumn) ??
    null;

  const availableOperators =
    selectedColumn === null
      ? []
      : filterOperatorsForType(selectedColumn.inferred_type);

  const geographyValues = geographySummary.geographies.map(
    (geography) => geography.value,
  );

  const coordinateReadyCount = geographySummary.geographies.filter(
    (geography) => geography.coordinate_status === "verified",
  ).length;

  const geographyByValue = new Map(
    geographySummary.geographies.map((geography) => [
      geography.value,
      geography,
    ]),
  );

  const segmentValues = segmentColumn
    ? observedValues(preview.rows, segmentColumn)
    : [];

  const segmentColumns = preview.columns.filter(
    (column) =>
      column.inferred_type === "string" ||
      column.inferred_type === "integer" ||
      column.inferred_type === "boolean",
  );

  const canAddFilter =
    selectedColumn !== null &&
    (!operatorRequiresValue(selectedFilterOperator) ||
      filterValue.trim().length > 0);

  function addFilterRule(): void {
    if (selectedColumn === null || !canAddFilter) {
      return;
    }

    const value = operatorRequiresValue(selectedFilterOperator)
      ? typedFilterValue(selectedColumn.inferred_type, filterValue.trim())
      : undefined;

    onAddFilter({
      id: [
        selectedFilterColumn,
        selectedFilterOperator,
        filterRules.length,
      ].join("-"),

      column: selectedFilterColumn,

      operator: selectedFilterOperator,

      ...(value === undefined
        ? {}
        : {
            value,
          }),
    });
  }

  return (
    <main className="analysis-population-shell">
      <header className="analysis-population-hero">
        <p className="analysis-population-hero__eyebrow">Population design</p>

        <h1>Configure Analysis</h1>

        <p>
          Define the exact rows, geographies, and segments included in this
          analysis.
        </p>
      </header>

      <section
        className="analysis-population-card"
        aria-labelledby={"population-selection-heading"}
      >
        <h2 id={"population-selection-heading"}>
          Filter and select population
        </h2>

        <p className="analysis-population-card__intro">
          Narrow the analysis population using columns from the selected
          dataset.
        </p>

        <label className="analysis-filter-field">
          <span>Filter column</span>

          <select
            aria-label="Filter column"
            value={selectedFilterColumn}
            onChange={(event) => {
              const columnName = event.target.value;

              const column = preview.columns.find(
                (candidate) => candidate.name === columnName,
              );

              const operators = column
                ? filterOperatorsForType(column.inferred_type)
                : [];

              onFilterColumnChange(
                columnName,
                column ? (operators[0]?.value ?? "equals") : null,
              );
            }}
          >
            <option value="">Choose a column</option>

            {preview.columns.map((column) => (
              <option key={column.name} value={column.name}>
                {column.name}
              </option>
            ))}
          </select>
        </label>

        {selectedColumn !== null && (
          <>
            <label className="analysis-filter-field">
              <span>Filter operator</span>

              <select
                aria-label={"Filter operator"}
                value={selectedFilterOperator}
                onChange={(event) => {
                  onFilterOperatorChange(event.target.value as FilterOperator);
                }}
              >
                {availableOperators.map((operator) => (
                  <option key={operator.value} value={operator.value}>
                    {operator.label}
                  </option>
                ))}
              </select>
            </label>

            {operatorRequiresValue(selectedFilterOperator) && (
              <label className="analysis-filter-field">
                <span>Filter value</span>

                <input
                  type={filterValueInputType(selectedColumn.inferred_type)}
                  aria-label={"Filter value"}
                  value={filterValue}
                  onChange={(event) => {
                    onFilterValueChange(event.target.value);
                  }}
                />
              </label>
            )}

            <button
              className="analysis-filter-add"
              type="button"
              disabled={!canAddFilter}
              onClick={addFilterRule}
            >
              Add filter
            </button>
          </>
        )}

        {filterRules.length > 0 && (
          <div className="analysis-filter-rules" aria-label={"Applied filters"}>
            {filterRules.map((rule) => (
              <div key={rule.id} className="analysis-filter-rule">
                <span>
                  {rule.column}
                  {" · "}
                  {filterOperatorLabel(rule.operator)}

                  {rule.value === undefined
                    ? ""
                    : ` · ${String(rule.value.value)}`}
                </span>

                <button
                  type="button"
                  aria-label={`Remove filter ${rule.column}`}
                  onClick={() => {
                    onRemoveFilter(rule.id);
                  }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        {estimator !== "off_policy_evaluation" && (
    <section
          className="analysis-geography-section"
          aria-labelledby={"geography-selection-heading"}
        >
          <div className="analysis-geography-section__header">
            <div>
              <p className="analysis-geography-section__eyebrow">
                Complete dataset coverage
              </p>

              <h3 id={"geography-selection-heading"}>Geography selection</h3>

              <p>
                Geography values come from the complete mapped unit column:{" "}
                {unitColumn}.
              </p>
            </div>
          </div>

          <div
            className="analysis-geography-summary"
            aria-label="Geography dataset summary"
          >
            <span>
              <strong>{geographySummary.total_geographies}</strong>
              geographies
            </span>

            {coordinatesRelevant ? (
              <>
                <span>
                  <strong>{coordinateReadyCount}</strong>
                  map-ready
                </span>

                <span>
                  <strong>
                    {geographySummary.total_geographies - coordinateReadyCount}
                  </strong>
                  coordinates required
                </span>
              </>
            ) : (
              <span>
                <strong>Not needed</strong>
                coordinates for this method
              </span>
            )}
          </div>

          {coordinatesRelevant ? (
            <AnalysisGeographyMapLoader
              geographies={geographySummary.geographies}
              selectedGeographies={selectedGeographies}
              excludedGeographies={excludedGeographies}
              onInclude={onSelectedGeographyChange}
              onExclude={onExcludedGeographyChange}
            />
          ) : null}

          <div
            className="analysis-geography-grid"
            role="region"
            aria-label="Geography selection cards"
            tabIndex={0}
          >
            {geographyValues.map((value) => {
              const geography = geographyByValue.get(value);

              return (
                <article
                  key={value}
                  className="analysis-geography-card"
                  aria-label={`Geography ${value}`}
                  data-state={
                    selectedGeographies.includes(value)
                      ? "included"
                      : excludedGeographies.includes(value)
                        ? "excluded"
                        : "neutral"
                  }
                >
                  <div className="analysis-geography-card__header">
                    <div>
                      <strong>{value}</strong>

                      <span>
                        {geography?.observation_count.toLocaleString("en-US") ??
                          "0"}{" "}
                        observations
                      </span>
                    </div>

                    {coordinatesRelevant ? (
                      <span
                        className="analysis-geography-card__status"
                        data-status={geography?.coordinate_status ?? "missing"}
                      >
                        {geography?.coordinate_status === "verified"
                          ? "Map ready"
                          : "Coordinates required"}
                      </span>
                    ) : null}
                  </div>

                  <div className="analysis-geography-card__metrics">
                    <span>
                      <small>Outcome total</small>
                      <strong>
                        {formatPopulationMetric(
                          geography?.metrics.outcome_sum ?? null,
                        )}
                      </strong>
                    </span>

                    <span>
                      <small>Spend total</small>
                      <strong>
                        {formatPopulationMetric(
                          geography?.metrics.spend_sum ?? null,
                        )}
                      </strong>
                    </span>

                    {Object.entries(geography?.metrics.covariate_sums ?? {})
                      .slice(0, 2)
                      .map(([metric, metricValue]) => (
                        <span key={metric}>
                          <small>{humanizeMetricName(metric)}</small>

                          <strong>{formatPopulationMetric(metricValue)}</strong>
                        </span>
                      ))}
                  </div>

                  <div className="analysis-geography-card__actions">
                    <label>
                      <input
                        type="checkbox"
                        aria-label={`Include geography ${value}`}
                        checked={selectedGeographies.includes(value)}
                        disabled={excludedGeographies.includes(value)}
                        onChange={(event) => {
                          onSelectedGeographyChange(
                            value,
                            event.target.checked,
                          );
                        }}
                      />
                      Include
                    </label>

                    <label>
                      <input
                        type="checkbox"
                        aria-label={`Exclude geography ${value}`}
                        checked={excludedGeographies.includes(value)}
                        disabled={selectedGeographies.includes(value)}
                        onChange={(event) => {
                          onExcludedGeographyChange(
                            value,
                            event.target.checked,
                          );
                        }}
                      />
                      Exclude
                    </label>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
    )}

        <section
          className="analysis-segment-section"
          aria-labelledby={"segment-selection-heading"}
        >
          <h3 id={"segment-selection-heading"}>Segment selection</h3>

          <label className="analysis-segment-field">
            <span>Segment column</span>

            <select
              aria-label={"Segment column"}
              value={segmentColumn}
              onChange={(event) => {
                onSegmentColumnChange(event.target.value);
              }}
            >
              <option value="">No segment selection</option>

              {segmentColumns.map((column) => (
                <option key={column.name} value={column.name}>
                  {column.name}
                </option>
              ))}
            </select>
          </label>

          {segmentValues.map((value) => (
            <div key={value} className="analysis-segment-option">
              <label>
                <input
                  type="checkbox"
                  aria-label={`Include segment ${value}`}
                  checked={selectedSegments.includes(value)}
                  disabled={excludedSegments.includes(value)}
                  onChange={(event) => {
                    onSelectedSegmentChange(value, event.target.checked);
                  }}
                />
                Include {value}
              </label>

              <label>
                <input
                  type="checkbox"
                  aria-label={`Exclude segment ${value}`}
                  checked={excludedSegments.includes(value)}
                  disabled={selectedSegments.includes(value)}
                  onChange={(event) => {
                    onExcludedSegmentChange(value, event.target.checked);
                  }}
                />
                Exclude {value}
              </label>
            </div>
          ))}
        </section>

        <button
          className="analysis-population-continue"
          type="button"
          onClick={onContinue}
        >
          Continue
        </button>
      </section>
    </main>
  );
}
