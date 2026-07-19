import type {
  DatasetPreview,
} from "@/lib/data-products/types";

import type {
  FilterOperator,
  FilterRule as RequestFilterRule,
  FilterValue,
} from "@/lib/analysis-configuration/request";

export type AnalysisFilterRule =
  RequestFilterRule & {
    id: string;
  };

type FilterOperatorOption = {
  value: FilterOperator;
  label: string;
};

type AnalysisFiltersStepProps = {
  preview: DatasetPreview;
  unitColumn: string;

  selectedFilterColumn: string;
  selectedFilterOperator:
    FilterOperator;
  filterValue: string;
  filterRules:
    AnalysisFilterRule[];

  selectedGeographies:
    string[];
  excludedGeographies:
    string[];

  segmentColumn: string;
  selectedSegments:
    string[];
  excludedSegments:
    string[];

  onFilterColumnChange: (
    columnName: string,
    defaultOperator:
      FilterOperator | null,
  ) => void;

  onFilterOperatorChange: (
    operator: FilterOperator,
  ) => void;

  onFilterValueChange: (
    value: string,
  ) => void;

  onAddFilter: (
    rule: AnalysisFilterRule,
  ) => void;

  onRemoveFilter: (
    ruleId: string,
  ) => void;

  onSelectedGeographyChange: (
    value: string,
    checked: boolean,
  ) => void;

  onExcludedGeographyChange: (
    value: string,
    checked: boolean,
  ) => void;

  onSegmentColumnChange: (
    value: string,
  ) => void;

  onSelectedSegmentChange: (
    value: string,
    checked: boolean,
  ) => void;

  onExcludedSegmentChange: (
    value: string,
    checked: boolean,
  ) => void;

  onContinue: () => void;
};

const EQUALITY_FILTER_OPERATORS:
  FilterOperatorOption[] = [
    {
      value: "equals",
      label: "Equals",
    },
    {
      value: "not_equals",
      label: "Not equals",
    },
  ];

const ORDERED_FILTER_OPERATORS:
  FilterOperatorOption[] = [
    {
      value: "greater_than",
      label: "Greater than",
    },
    {
      value:
        "greater_than_or_equal",
      label:
        "Greater than or equal",
    },
    {
      value: "less_than",
      label: "Less than",
    },
    {
      value:
        "less_than_or_equal",
      label:
        "Less than or equal",
    },
  ];

const NULL_FILTER_OPERATORS:
  FilterOperatorOption[] = [
    {
      value: "is_null",
      label: "Is null",
    },
    {
      value: "is_not_null",
      label: "Is not null",
    },
  ];

function filterOperatorsForType(
  inferredType: string,
): FilterOperatorOption[] {
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
    inferredType === "integer"
    || inferredType === "float"
    || inferredType === "date"
    || inferredType === "datetime"
  ) {
    return [
      ...EQUALITY_FILTER_OPERATORS,
      ...ORDERED_FILTER_OPERATORS,
      ...NULL_FILTER_OPERATORS,
    ];
  }

  return [
    ...EQUALITY_FILTER_OPERATORS,
    ...NULL_FILTER_OPERATORS,
  ];
}

function filterValueInputType(
  inferredType: string,
): "text" | "number" | "date" {
  if (
    inferredType === "integer"
    || inferredType === "float"
  ) {
    return "number";
  }

  if (
    inferredType === "date"
    || inferredType === "datetime"
  ) {
    return "date";
  }

  return "text";
}

function operatorRequiresValue(
  operator: FilterOperator,
): boolean {
  return (
    operator !== "is_null"
    && operator !== "is_not_null"
  );
}

function filterOperatorLabel(
  operator: FilterOperator,
): string {
  const options = [
    ...EQUALITY_FILTER_OPERATORS,
    ...ORDERED_FILTER_OPERATORS,
    ...NULL_FILTER_OPERATORS,
    {
      value: "contains" as const,
      label: "Contains",
    },
  ];

  return (
    options.find(
      (option) =>
        option.value
        === operator,
    )?.label
    ?? operator
  );
}

function typedFilterValue(
  inferredType: string,
  rawValue: string,
): FilterValue {
  if (
    inferredType === "integer"
    || inferredType === "float"
  ) {
    return {
      type: "number",
      value: Number(
        rawValue,
      ),
    };
  }

  if (
    inferredType === "date"
    || inferredType === "datetime"
  ) {
    return {
      type: "date",
      value: rawValue,
    };
  }

  if (
    inferredType
    === "boolean"
  ) {
    return {
      type: "boolean",
      value:
        rawValue
          .toLocaleLowerCase()
        === "true",
    };
  }

  return {
    type: "string",
    value: rawValue,
  };
}

function observedValues(
  rows:
    Array<
      Record<
        string,
        unknown
      >
    >,
  columnName: string,
): string[] {
  if (!columnName) {
    return [];
  }

  const values:
    string[] = [];

  const seen =
    new Set<string>();

  for (
    const row
    of rows
  ) {
    const rawValue =
      row[columnName];

    if (
      rawValue === null
      || rawValue
        === undefined
    ) {
      continue;
    }

    const value =
      String(
        rawValue,
      ).trim();

    if (
      value.length === 0
      || seen.has(
        value,
      )
    ) {
      continue;
    }

    seen.add(
      value,
    );

    values.push(
      value,
    );
  }

  return values;
}

export function AnalysisFiltersStep({
  preview,
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
  const selectedColumn =
    preview.columns.find(
      (column) =>
        column.name
        === selectedFilterColumn,
    ) ?? null;

  const availableOperators =
    selectedColumn === null
      ? []
      : filterOperatorsForType(
          selectedColumn
            .inferred_type,
        );

  const geographyValues =
    observedValues(
      preview.rows,
      unitColumn,
    );

  const segmentValues =
    segmentColumn
      ? observedValues(
          preview.rows,
          segmentColumn,
        )
      : [];

  const segmentColumns =
    preview.columns.filter(
      (column) =>
        column.inferred_type
          === "string"
        || column.inferred_type
          === "integer"
        || column.inferred_type
          === "boolean",
    );

  const canAddFilter =
    selectedColumn !== null
    && (
      !operatorRequiresValue(
        selectedFilterOperator,
      )
      || filterValue
        .trim()
        .length > 0
    );

  function addFilterRule():
    void {
    if (
      selectedColumn === null
      || !canAddFilter
    ) {
      return;
    }

    const value =
      operatorRequiresValue(
        selectedFilterOperator,
      )
        ? typedFilterValue(
            selectedColumn
              .inferred_type,
            filterValue
              .trim(),
          )
        : undefined;

    onAddFilter({
      id: [
        selectedFilterColumn,
        selectedFilterOperator,
        filterRules.length,
      ].join("-"),

      column:
        selectedFilterColumn,

      operator:
        selectedFilterOperator,

      ...(value === undefined
        ? {}
        : {
            value,
          }),
    });
  }

  return (
    <main>
      <h1>
        Configure Analysis
      </h1>

      <section
        aria-labelledby={
          "population-selection-heading"
        }
      >
        <h2
          id={
            "population-selection-heading"
          }
        >
          Filter and select population
        </h2>

        <p>
          Narrow the analysis population using
          columns from the selected dataset.
        </p>

        <label>
          <span>
            Filter column
          </span>

          <select
            aria-label="Filter column"
            value={
              selectedFilterColumn
            }
            onChange={(event) => {
              const columnName =
                event.target.value;

              const column =
                preview.columns.find(
                  (candidate) =>
                    candidate.name
                    === columnName,
                );

              const operators =
                column
                  ? filterOperatorsForType(
                      column
                        .inferred_type,
                    )
                  : [];

              onFilterColumnChange(
                columnName,
                column
                  ? (
                      operators[0]
                        ?.value
                      ?? "equals"
                    )
                  : null,
              );
            }}
          >
            <option value="">
              Choose a column
            </option>

            {preview.columns.map(
              (column) => (
                <option
                  key={
                    column.name
                  }
                  value={
                    column.name
                  }
                >
                  {column.name}
                </option>
              ),
            )}
          </select>
        </label>

        {selectedColumn
          !== null
          && (
            <>
              <label>
                <span>
                  Filter operator
                </span>

                <select
                  aria-label={
                    "Filter operator"
                  }
                  value={
                    selectedFilterOperator
                  }
                  onChange={(
                    event,
                  ) => {
                    onFilterOperatorChange(
                      event.target.value as FilterOperator,
                    );
                  }}
                >
                  {availableOperators
                    .map(
                      (
                        operator,
                      ) => (
                        <option
                          key={
                            operator
                              .value
                          }
                          value={
                            operator
                              .value
                          }
                        >
                          {
                            operator
                              .label
                          }
                        </option>
                      ),
                    )}
                </select>
              </label>

              {operatorRequiresValue(
                selectedFilterOperator,
              ) && (
                <label>
                  <span>
                    Filter value
                  </span>

                  <input
                    type={
                      filterValueInputType(
                        selectedColumn
                          .inferred_type,
                      )
                    }
                    aria-label={
                      "Filter value"
                    }
                    value={
                      filterValue
                    }
                    onChange={(
                      event,
                    ) => {
                      onFilterValueChange(
                        event.target
                          .value,
                      );
                    }}
                  />
                </label>
              )}

              <button
                type="button"
                disabled={
                  !canAddFilter
                }
                onClick={
                  addFilterRule
                }
              >
                Add filter
              </button>
            </>
          )}

        {filterRules.length
          > 0
          && (
            <div
              aria-label={
                "Applied filters"
              }
            >
              {filterRules.map(
                (rule) => (
                  <div
                    key={
                      rule.id
                    }
                  >
                    <span>
                      {rule.column}
                      {" · "}
                      {
                        filterOperatorLabel(
                          rule.operator,
                        )
                      }

                      {rule.value
                        === undefined
                        ? ""
                        : ` · ${String(
                            rule
                              .value
                              .value,
                          )}`}
                    </span>

                    <button
                      type="button"
                      aria-label={
                        `Remove filter ${rule.column}`
                      }
                      onClick={() => {
                        onRemoveFilter(
                          rule.id,
                        );
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ),
              )}
            </div>
          )}

        <section
          aria-labelledby={
            "geography-selection-heading"
          }
        >
          <h3
            id={
              "geography-selection-heading"
            }
          >
            Geography selection
          </h3>

          <p>
            Geography values come from the mapped
            unit column: {unitColumn}.
          </p>

          {geographyValues.map(
            (value) => (
              <div
                key={value}
              >
                <label>
                  <input
                    type="checkbox"
                    aria-label={
                      `Include geography ${value}`
                    }
                    checked={
                      selectedGeographies
                        .includes(
                          value,
                        )
                    }
                    disabled={
                      excludedGeographies
                        .includes(
                          value,
                        )
                    }
                    onChange={(
                      event,
                    ) => {
                      onSelectedGeographyChange(
                        value,
                        event.target
                          .checked,
                      );
                    }}
                  />

                  Include {value}
                </label>

                <label>
                  <input
                    type="checkbox"
                    aria-label={
                      `Exclude geography ${value}`
                    }
                    checked={
                      excludedGeographies
                        .includes(
                          value,
                        )
                    }
                    disabled={
                      selectedGeographies
                        .includes(
                          value,
                        )
                    }
                    onChange={(
                      event,
                    ) => {
                      onExcludedGeographyChange(
                        value,
                        event.target
                          .checked,
                      );
                    }}
                  />

                  Exclude {value}
                </label>
              </div>
            ),
          )}
        </section>

        <section
          aria-labelledby={
            "segment-selection-heading"
          }
        >
          <h3
            id={
              "segment-selection-heading"
            }
          >
            Segment selection
          </h3>

          <label>
            <span>
              Segment column
            </span>

            <select
              aria-label={
                "Segment column"
              }
              value={
                segmentColumn
              }
              onChange={(
                event,
              ) => {
                onSegmentColumnChange(
                  event.target
                    .value,
                );
              }}
            >
              <option value="">
                No segment selection
              </option>

              {segmentColumns.map(
                (column) => (
                  <option
                    key={
                      column.name
                    }
                    value={
                      column.name
                    }
                  >
                    {column.name}
                  </option>
                ),
              )}
            </select>
          </label>

          {segmentValues.map(
            (value) => (
              <div
                key={value}
              >
                <label>
                  <input
                    type="checkbox"
                    aria-label={
                      `Include segment ${value}`
                    }
                    checked={
                      selectedSegments
                        .includes(
                          value,
                        )
                    }
                    disabled={
                      excludedSegments
                        .includes(
                          value,
                        )
                    }
                    onChange={(
                      event,
                    ) => {
                      onSelectedSegmentChange(
                        value,
                        event.target
                          .checked,
                      );
                    }}
                  />

                  Include {value}
                </label>

                <label>
                  <input
                    type="checkbox"
                    aria-label={
                      `Exclude segment ${value}`
                    }
                    checked={
                      excludedSegments
                        .includes(
                          value,
                        )
                    }
                    disabled={
                      selectedSegments
                        .includes(
                          value,
                        )
                    }
                    onChange={(
                      event,
                    ) => {
                      onExcludedSegmentChange(
                        value,
                        event.target
                          .checked,
                      );
                    }}
                  />

                  Exclude {value}
                </label>
              </div>
            ),
          )}
        </section>

        <button
          type="button"
          onClick={
            onContinue
          }
        >
          Continue
        </button>
      </section>
    </main>
  );
}
