import type { AnalysisEstimatorType } from "@/lib/analysis-configuration/request";

import type {
  DatasetPreview,
  GeographySummary,
  GeographySummaryItem,
} from "@/lib/data-products/types";

type AnalysisTreatmentControlStepProps = {
  preview: DatasetPreview;
  geographySummary: GeographySummary;
  estimator: AnalysisEstimatorType;

  unitColumn: string;

  treatmentColumn: string | null;
  treatmentValue: string | null;
  controlValue: string | null;

  treatedUnit: string;
  donorPool: string[];

  treatedGeoAssignments: string[];
  controlGeoAssignments: string[];

  policyName: string;
  behaviorPropensityColumn: string;
  targetPropensityColumn: string;

  onTreatedUnitChange: (value: string) => void;

  onDonorChange: (value: string, checked: boolean) => void;

  onTreatedGeoChange: (value: string, checked: boolean) => void;

  onControlGeoChange: (value: string, checked: boolean) => void;

  onPolicyNameChange: (value: string) => void;

  onBehaviorPropensityColumnChange: (value: string) => void;

  onTargetPropensityColumnChange: (value: string) => void;

  onContinue: () => void;
};

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

function formatMetric(value: number | null): string {
  if (value === null) {
    return "Not available";
  }

  return new Intl.NumberFormat("en-US", {
    notation: Math.abs(value) >= 10_000 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value);
}

function humanizeMetricName(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function GeographyEvidence({
  geography,
}: {
  geography: GeographySummaryItem | undefined;
}) {
  if (geography === undefined) {
    return (
      <span className="analysis-assignment-evidence">
        <small>Dataset evidence unavailable</small>
      </span>
    );
  }

  const firstCovariate = Object.entries(geography.metrics.covariate_sums)[0];

  return (
    <span className="analysis-assignment-evidence">
      <span>
        <strong>{geography.observation_count.toLocaleString("en-US")}</strong>
        <small>observations</small>
      </span>

      <span>
        <strong>{formatMetric(geography.metrics.outcome_sum)}</strong>
        <small>outcome</small>
      </span>

      {geography.metrics.spend_sum !== null && (
        <span>
          <strong>{formatMetric(geography.metrics.spend_sum)}</strong>
          <small>spend</small>
        </span>
      )}

      {firstCovariate !== undefined && (
        <span>
          <strong>{formatMetric(firstCovariate[1])}</strong>
          <small>{humanizeMetricName(firstCovariate[0])}</small>
        </span>
      )}
    </span>
  );
}

export function AnalysisTreatmentControlStep({
  preview,
  geographySummary,
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
  const previewUnitValues = observedValues(preview.rows, unitColumn);

  const unitValues =
    geographySummary.geographies.length > 0
      ? geographySummary.geographies.map((geography) => geography.value)
      : previewUnitValues;

  const geographyByValue = new Map(
    geographySummary.geographies.map((geography) => [
      geography.value,
      geography,
    ]),
  );

  const numericColumns = preview.columns.filter(
    (column) =>
      column.inferred_type === "integer" || column.inferred_type === "float",
  );

  const syntheticReady =
    treatedUnit.length > 0 &&
    donorPool.length >= 2 &&
    !donorPool.includes(treatedUnit);

  const geoOverlap = treatedGeoAssignments.filter((value) =>
    controlGeoAssignments.includes(value),
  );

  const geoReady =
    treatedGeoAssignments.length > 0 &&
    controlGeoAssignments.length > 0 &&
    geoOverlap.length === 0;

  const offPolicyReady =
    policyName.trim().length > 0 &&
    behaviorPropensityColumn.length > 0 &&
    targetPropensityColumn.length > 0;

  const canContinue =
    estimator === "difference_in_differences" ||
    estimator === "marketing_mix_model" ||
    (estimator === "synthetic_control" && syntheticReady) ||
    (estimator === "geo_holdout" && geoReady) ||
    (estimator === "off_policy_evaluation" && offPolicyReady);

  const readinessMessage =
    estimator === "difference_in_differences"
      ? "Mapped treatment and control values are ready."
      : estimator === "synthetic_control"
        ? syntheticReady
          ? `${donorPool.length} donors selected for ${treatedUnit}.`
          : "Select one treated unit and at least two donors."
        : estimator === "geo_holdout"
          ? geoReady
            ? `${treatedGeoAssignments.length} treated and ${controlGeoAssignments.length} control geographies assigned.`
            : "Assign at least one treated and one control geography."
          : estimator === "marketing_mix_model"
            ? "No assignment is required for this estimator."
            : offPolicyReady
              ? "Policy and propensity columns are ready."
              : "Complete the policy and propensity configuration.";

  return (
    <main className="analysis-assignment-shell">
      <header className="analysis-assignment-hero">
        <p className="analysis-assignment-hero__eyebrow">Analysis setup</p>

        <h1>Configure Analysis</h1>

        <p>
          Define the populations the estimator will compare while preserving the
          mapped dataset evidence.
        </p>
      </header>

      <section
        className="analysis-assignment-card"
        aria-labelledby="treatment-control-heading"
      >
        <header className="analysis-assignment-card__header">
          <span className="analysis-assignment-card__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M8 5H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3M16 5h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-3M8 12h8M12 8l4 4-4 4"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>

          <span>
            <h2 id="treatment-control-heading">Treatment and control setup</h2>

            <p>
              Configure comparison groups using complete scoped dataset values.
            </p>
          </span>

          <span className="analysis-assignment-card__scope">
            <strong>{unitValues.length}</strong>
            <small>
              available {unitValues.length === 1 ? "unit" : "units"}
            </small>
          </span>
        </header>

        {estimator === "difference_in_differences" && (
          <div className="analysis-assignment-content">
            <div className="analysis-assignment-guidance" role="note">
              <span aria-hidden="true">✓</span>

              <p>
                <strong>
                  Assignment is locked to the saved semantic mapping.
                </strong>

                <small>
                  This keeps the configured analysis consistent with the
                  reviewed dataset definition.
                </small>
              </p>
            </div>

            <div className="analysis-mapped-definition">
              <article>
                <small>Assignment column</small>
                <strong>{treatmentColumn ?? "Not mapped"}</strong>

                <p>{`Treatment column: ${treatmentColumn ?? "Not mapped"}`}</p>
              </article>

              <article data-tone="treated">
                <small>Treatment value</small>
                <strong>{treatmentValue ?? "Not mapped"}</strong>

                <p>{`Treatment value: ${treatmentValue ?? "Not mapped"}`}</p>
              </article>

              <article data-tone="control">
                <small>Control value</small>
                <strong>{controlValue ?? "Not mapped"}</strong>

                <p>{`Control value: ${controlValue ?? "Not mapped"}`}</p>
              </article>
            </div>
          </div>
        )}

        {estimator === "synthetic_control" && (
          <div className="analysis-assignment-content">
            <div className="analysis-assignment-summary">
              <span data-tone="treated">
                <strong>{treatedUnit || "None"}</strong>
                <small>Treated unit</small>
              </span>

              <span data-tone="control">
                <strong>{donorPool.length}</strong>
                <small>Selected donors</small>
              </span>

              <span>
                <strong>2+</strong>
                <small>Minimum donors</small>
              </span>
            </div>

            <div className="analysis-synthetic-layout">
              <section className="analysis-assignment-panel">
                <header>
                  <span>
                    <small>Primary unit</small>
                    <h3>Select treated unit</h3>
                  </span>

                  <span
                    className="analysis-assignment-panel__count"
                    data-tone="treated"
                  >
                    1 required
                  </span>
                </header>

                <label className="analysis-assignment-select">
                  <span>Treated unit</span>

                  <select
                    aria-label="Treated unit"
                    value={treatedUnit}
                    onChange={(event) => {
                      onTreatedUnitChange(event.target.value);
                    }}
                  >
                    <option value="">Choose treated unit</option>

                    {unitValues.map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>

                {treatedUnit ? (
                  <article className="analysis-selected-unit">
                    <span>
                      <small>Selected treatment</small>
                      <strong>{treatedUnit}</strong>
                    </span>

                    <GeographyEvidence
                      geography={geographyByValue.get(treatedUnit)}
                    />
                  </article>
                ) : (
                  <p className="analysis-assignment-empty">
                    Choose the unit that received the intervention.
                  </p>
                )}
              </section>

              <fieldset className="analysis-assignment-panel analysis-donor-panel">
                <legend className="sr-only">Donor pool</legend>

                <header>
                  <span>
                    <small>Comparison population</small>
                    <h3>Build donor pool</h3>
                  </span>

                  <span
                    className="analysis-assignment-panel__count"
                    data-tone="control"
                  >
                    {donorPool.length} selected
                  </span>
                </header>

                <div className="analysis-assignment-list">
                  {unitValues.map((value) => {
                    const checked = donorPool.includes(value);

                    const disabled = treatedUnit === value;

                    return (
                      <label
                        className="analysis-assignment-option"
                        data-selected={checked}
                        data-disabled={disabled}
                        key={value}
                      >
                        <input
                          type="checkbox"
                          aria-label={`Donor ${value}`}
                          checked={checked}
                          disabled={disabled}
                          onChange={(event) => {
                            onDonorChange(value, event.target.checked);
                          }}
                        />

                        <span className="analysis-assignment-option__body">
                          <span className="analysis-assignment-option__title">
                            <strong>{value}</strong>

                            {disabled && <small>Treated unit</small>}
                          </span>

                          <GeographyEvidence
                            geography={geographyByValue.get(value)}
                          />
                        </span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            </div>
          </div>
        )}

        {estimator === "geo_holdout" && (
          <div className="analysis-assignment-content">
            <div className="analysis-assignment-summary">
              <span data-tone="treated">
                <strong>{treatedGeoAssignments.length}</strong>
                <small>Treated</small>
              </span>

              <span data-tone="control">
                <strong>{controlGeoAssignments.length}</strong>
                <small>Control</small>
              </span>

              <span>
                <strong>
                  {unitValues.length -
                    treatedGeoAssignments.length -
                    controlGeoAssignments.length}
                </strong>
                <small>Unassigned</small>
              </span>
            </div>

            <div className="analysis-assignment-guidance" role="note">
              <span aria-hidden="true">i</span>

              <p>
                <strong>Each geography can belong to only one group.</strong>

                <small>
                  Assignment controls disable automatically to prevent
                  treatment/control overlap.
                </small>
              </p>
            </div>

            <fieldset className="analysis-geography-assignment">
              <legend className="sr-only">Geography assignment</legend>

              <header className="analysis-geography-assignment__columns">
                <span>Geography evidence</span>
                <span>Treated</span>
                <span>Control</span>
              </header>

              <div className="analysis-geography-assignment__list">
                {unitValues.map((value) => {
                  const geography = geographyByValue.get(value);

                  const treated = treatedGeoAssignments.includes(value);

                  const control = controlGeoAssignments.includes(value);

                  return (
                    <article
                      className="analysis-geography-row"
                      data-assignment={
                        treated ? "treated" : control ? "control" : "unassigned"
                      }
                      key={value}
                    >
                      <span className="analysis-geography-row__identity">
                        <span>
                          <strong>{value}</strong>

                          <small>
                            {geography?.coordinate_status === "verified"
                              ? "Map ready"
                              : "Coordinates required"}
                          </small>
                        </span>

                        <GeographyEvidence geography={geography} />
                      </span>

                      <label
                        className="analysis-assignment-choice"
                        data-tone="treated"
                        data-selected={treated}
                      >
                        <input
                          type="checkbox"
                          aria-label={`Treat geography ${value}`}
                          checked={treated}
                          disabled={control}
                          onChange={(event) => {
                            onTreatedGeoChange(value, event.target.checked);
                          }}
                        />

                        <span>Treat</span>
                      </label>

                      <label
                        className="analysis-assignment-choice"
                        data-tone="control"
                        data-selected={control}
                      >
                        <input
                          type="checkbox"
                          aria-label={`Control geography ${value}`}
                          checked={control}
                          disabled={treated}
                          onChange={(event) => {
                            onControlGeoChange(value, event.target.checked);
                          }}
                        />

                        <span>Control</span>
                      </label>
                    </article>
                  );
                })}
              </div>
            </fieldset>

            {geoOverlap.length > 0 && (
              <p className="analysis-assignment-error" role="alert">
                Geography values cannot be both treated and control.
              </p>
            )}
          </div>
        )}

        {estimator === "marketing_mix_model" && (
          <div className="analysis-assignment-content">
            <article className="analysis-no-assignment">
              <span className="analysis-no-assignment__icon" aria-hidden="true">
                ✓
              </span>

              <span>
                <h3>No group assignment required</h3>

                <p>
                  Marketing Mix Modeling does not require treatment/control
                  assignment.
                </p>

                <small>
                  Channel-level exposure and outcome settings are configured in
                  the next step.
                </small>
              </span>
            </article>
          </div>
        )}

        {estimator === "off_policy_evaluation" && (
          <div className="analysis-assignment-content">
            <div className="analysis-assignment-guidance" role="note">
              <span aria-hidden="true">i</span>

              <p>
                <strong>
                  Define the evaluated policy and its logged probabilities.
                </strong>

                <small>
                  Only numeric dataset columns are available for propensity
                  selection.
                </small>
              </p>
            </div>

            <div className="analysis-policy-form">
              <label>
                <span>
                  <strong>Policy name</strong>
                  <small>A recognizable name for the evaluated policy.</small>
                </span>

                <input
                  type="text"
                  aria-label="Policy name"
                  value={policyName}
                  placeholder="Example: New recommendation policy"
                  onChange={(event) => {
                    onPolicyNameChange(event.target.value);
                  }}
                />
              </label>

              <label>
                <span>
                  <strong>Behavior propensity column</strong>
                  <small>Probability used by the logged policy.</small>
                </span>

                <select
                  aria-label="Behavior propensity column"
                  value={behaviorPropensityColumn}
                  onChange={(event) => {
                    onBehaviorPropensityColumnChange(event.target.value);
                  }}
                >
                  <option value="">Choose behavior propensity</option>

                  {numericColumns.map((column) => (
                    <option key={column.name} value={column.name}>
                      {column.name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <span>
                  <strong>Target propensity column</strong>
                  <small>
                    Probability assigned by the policy being evaluated.
                  </small>
                </span>

                <select
                  aria-label="Target propensity column"
                  value={targetPropensityColumn}
                  onChange={(event) => {
                    onTargetPropensityColumnChange(event.target.value);
                  }}
                >
                  <option value="">Choose target propensity</option>

                  {numericColumns.map((column) => (
                    <option key={column.name} value={column.name}>
                      {column.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        )}

        <footer className="analysis-assignment-actions">
          <span data-ready={canContinue}>
            <strong>
              {canContinue ? "Ready to continue" : "Assignment incomplete"}
            </strong>

            <small>{readinessMessage}</small>
          </span>

          <button type="button" disabled={!canContinue} onClick={onContinue}>
            Continue
            <span aria-hidden="true">→</span>
          </button>
        </footer>
      </section>
    </main>
  );
}
