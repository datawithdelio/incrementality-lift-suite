import type {
  AnalysisEstimatorType,
} from "@/lib/analysis-configuration/request";

import type {
  DatasetPreview,
} from "@/lib/data-products/types";

type AnalysisTreatmentControlStepProps = {
  preview: DatasetPreview;
  estimator:
    AnalysisEstimatorType;

  unitColumn: string;

  treatmentColumn:
    string | null;
  treatmentValue:
    string | null;
  controlValue:
    string | null;

  treatedUnit: string;
  donorPool: string[];

  treatedGeoAssignments:
    string[];
  controlGeoAssignments:
    string[];

  policyName: string;

  behaviorPropensityColumn:
    string;

  targetPropensityColumn:
    string;

  onTreatedUnitChange: (
    value: string,
  ) => void;

  onDonorChange: (
    value: string,
    checked: boolean,
  ) => void;

  onTreatedGeoChange: (
    value: string,
    checked: boolean,
  ) => void;

  onControlGeoChange: (
    value: string,
    checked: boolean,
  ) => void;

  onPolicyNameChange: (
    value: string,
  ) => void;

  onBehaviorPropensityColumnChange: (
    value: string,
  ) => void;

  onTargetPropensityColumnChange: (
    value: string,
  ) => void;

  onContinue: () => void;
};

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

export function AnalysisTreatmentControlStep({
  preview,
  estimator,
  unitColumn,
  treatmentColumn,
  treatmentValue,
  controlValue,
  treatedUnit,
  donorPool,
  treatedGeoAssignments,
  controlGeoAssignments,
  policyName,
  behaviorPropensityColumn,
  targetPropensityColumn,
  onTreatedUnitChange,
  onDonorChange,
  onTreatedGeoChange,
  onControlGeoChange,
  onPolicyNameChange,
  onBehaviorPropensityColumnChange,
  onTargetPropensityColumnChange,
  onContinue,
}: AnalysisTreatmentControlStepProps) {
  const unitValues =
    observedValues(
      preview.rows,
      unitColumn,
    );

  const numericColumns =
    preview.columns.filter(
      (column) =>
        column.inferred_type
          === "integer"
        || column.inferred_type
          === "float",
    );

  const syntheticReady =
    treatedUnit.length > 0
    && donorPool.length >= 2
    && !donorPool.includes(
      treatedUnit,
    );

  const geoReady =
    treatedGeoAssignments
      .length > 0
    && controlGeoAssignments
      .length > 0
    && !treatedGeoAssignments
      .some(
        (value) =>
          controlGeoAssignments
            .includes(
              value,
            ),
      );

  const offPolicyReady =
    policyName
      .trim()
      .length > 0
    && behaviorPropensityColumn
      .length > 0
    && targetPropensityColumn
      .length > 0;

  return (
    <main>
      <h1>
        Configure Analysis
      </h1>

      <section
        aria-labelledby={
          "treatment-control-heading"
        }
      >
        <h2
          id={
            "treatment-control-heading"
          }
        >
          Treatment and control setup
        </h2>

        {estimator
          === "difference_in_differences"
          && (
            <>
              <p>
                Treatment assignment comes from
                the saved semantic mapping.
              </p>

              <p>
                Treatment column:{" "}
                {treatmentColumn}
              </p>

              <p>
                Treatment value:{" "}
                {treatmentValue}
              </p>

              <p>
                Control value:{" "}
                {controlValue}
              </p>

              <button
                type="button"
                onClick={
                  onContinue
                }
              >
                Continue
              </button>
            </>
          )}

        {estimator
          === "synthetic_control"
          && (
            <>
              <label>
                <span>
                  Treated unit
                </span>

                <select
                  aria-label={
                    "Treated unit"
                  }
                  value={
                    treatedUnit
                  }
                  onChange={(
                    event,
                  ) => {
                    onTreatedUnitChange(
                      event.target
                        .value,
                    );
                  }}
                >
                  <option value="">
                    Choose treated unit
                  </option>

                  {unitValues.map(
                    (value) => (
                      <option
                        key={value}
                        value={value}
                      >
                        {value}
                      </option>
                    ),
                  )}
                </select>
              </label>

              <fieldset>
                <legend>
                  Donor pool
                </legend>

                {unitValues.map(
                  (value) => (
                    <label
                      key={value}
                    >
                      <input
                        type="checkbox"
                        aria-label={
                          `Donor ${value}`
                        }
                        checked={
                          donorPool
                            .includes(
                              value,
                            )
                        }
                        disabled={
                          treatedUnit
                          === value
                        }
                        onChange={(
                          event,
                        ) => {
                          onDonorChange(
                            value,
                            event.target
                              .checked,
                          );
                        }}
                      />

                      {value}
                    </label>
                  ),
                )}
              </fieldset>

              <button
                type="button"
                disabled={
                  !syntheticReady
                }
                onClick={
                  onContinue
                }
              >
                Continue
              </button>
            </>
          )}

        {estimator
          === "geo_holdout"
          && (
            <>
              <fieldset>
                <legend>
                  Geography assignment
                </legend>

                {unitValues.map(
                  (value) => (
                    <div
                      key={value}
                    >
                      <label>
                        <input
                          type="checkbox"
                          aria-label={
                            `Treat geography ${value}`
                          }
                          checked={
                            treatedGeoAssignments
                              .includes(
                                value,
                              )
                          }
                          disabled={
                            controlGeoAssignments
                              .includes(
                                value,
                              )
                          }
                          onChange={(
                            event,
                          ) => {
                            onTreatedGeoChange(
                              value,
                              event.target
                                .checked,
                            );
                          }}
                        />

                        Treat {value}
                      </label>

                      <label>
                        <input
                          type="checkbox"
                          aria-label={
                            `Control geography ${value}`
                          }
                          checked={
                            controlGeoAssignments
                              .includes(
                                value,
                              )
                          }
                          disabled={
                            treatedGeoAssignments
                              .includes(
                                value,
                              )
                          }
                          onChange={(
                            event,
                          ) => {
                            onControlGeoChange(
                              value,
                              event.target
                                .checked,
                            );
                          }}
                        />

                        Control {value}
                      </label>
                    </div>
                  ),
                )}
              </fieldset>

              <button
                type="button"
                disabled={
                  !geoReady
                }
                onClick={
                  onContinue
                }
              >
                Continue
              </button>
            </>
          )}

        {estimator
          === "marketing_mix_model"
          && (
            <>
              <p>
                Marketing Mix Modeling does not
                require treatment/control assignment.
              </p>

              <button
                type="button"
                onClick={
                  onContinue
                }
              >
                Continue
              </button>
            </>
          )}

        {estimator
          === "off_policy_evaluation"
          && (
            <>
              <label>
                <span>
                  Policy name
                </span>

                <input
                  type="text"
                  aria-label={
                    "Policy name"
                  }
                  value={
                    policyName
                  }
                  onChange={(
                    event,
                  ) => {
                    onPolicyNameChange(
                      event.target
                        .value,
                    );
                  }}
                />
              </label>

              <label>
                <span>
                  Behavior propensity column
                </span>

                <select
                  aria-label={
                    "Behavior propensity column"
                  }
                  value={
                    behaviorPropensityColumn
                  }
                  onChange={(
                    event,
                  ) => {
                    onBehaviorPropensityColumnChange(
                      event.target
                        .value,
                    );
                  }}
                >
                  <option value="">
                    Choose behavior propensity
                  </option>

                  {numericColumns.map(
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

              <label>
                <span>
                  Target propensity column
                </span>

                <select
                  aria-label={
                    "Target propensity column"
                  }
                  value={
                    targetPropensityColumn
                  }
                  onChange={(
                    event,
                  ) => {
                    onTargetPropensityColumnChange(
                      event.target
                        .value,
                    );
                  }}
                >
                  <option value="">
                    Choose target propensity
                  </option>

                  {numericColumns.map(
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

              <button
                type="button"
                disabled={
                  !offPolicyReady
                }
                onClick={
                  onContinue
                }
              >
                Continue
              </button>
            </>
          )}
      </section>
    </main>
  );
}
