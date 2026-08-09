import type {
  AnalysisEstimatorType,
  OffPolicyMethod,
} from "@/lib/analysis-configuration/request";

import type { DatasetPreview } from "@/lib/data-products/types";

type GeoCoordinateDraft = {
  latitude: string;
  longitude: string;
  source: "dataset" | "manual";
};

type AnalysisEstimatorSettingsStepProps = {
  preview: DatasetPreview;
  estimator: AnalysisEstimatorType;

  treatedGeoAssignments: string[];
  controlGeoAssignments: string[];

  geoCoordinates: Record<string, GeoCoordinateDraft>;

  geoOutcomeKind: string;

  mediaChannels: string[];
  controlColumns: string[];
  aggregateSpendColumn: string | null;
  mappedOutcomeColumn: string;

  mmmSeasonalityPeriod: string;
  mmmOutcomeKind: string;

  mmmAdstockDecay: Record<string, string>;

  mmmSaturationHalfSpend: Record<string, string>;

  rewardColumn: string;
  expectedRewardColumn: string;
  primaryMethod: OffPolicyMethod;

  onGeoOutcomeKindChange: (value: string) => void;

  onGeoCoordinateChange: (
    geography: string,
    field: "latitude" | "longitude",
    value: string,
  ) => void;

  onMmmSeasonalityPeriodChange: (value: string) => void;

  onMmmAdstockDecayChange: (channel: string, value: string) => void;

  onMmmSaturationHalfSpendChange: (channel: string, value: string) => void;

  onRewardColumnChange: (value: string) => void;

  onExpectedRewardColumnChange: (value: string) => void;

  onPrimaryMethodChange: (value: OffPolicyMethod) => void;

  onContinue: () => void;
};

function coordinateValidationMessage(
  coordinate: GeoCoordinateDraft | undefined,
): string | null {
  if (coordinate === undefined) {
    return "Latitude and longitude are required.";
  }

  const latitudeText = coordinate.latitude.trim();

  const longitudeText = coordinate.longitude.trim();

  if (latitudeText.length > 0) {
    const latitude = Number(latitudeText);

    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
      return "Latitude must be a number between -90 and 90.";
    }
  }

  if (longitudeText.length > 0) {
    const longitude = Number(longitudeText);

    if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      return "Longitude must be a number between -180 and 180.";
    }
  }

  if (latitudeText.length === 0 || longitudeText.length === 0) {
    return "Latitude and longitude are required.";
  }

  return null;
}

function estimatorTitle(estimator: AnalysisEstimatorType): string {
  switch (estimator) {
    case "difference_in_differences":
      return "Difference in Differences";

    case "synthetic_control":
      return "Synthetic Control";

    case "geo_holdout":
      return "Geo Holdout";

    case "marketing_mix_model":
      return "Marketing Mix Modeling";

    case "off_policy_evaluation":
      return "Off-policy Evaluation";
  }
}

export function AnalysisEstimatorSettingsStep({
  preview,
  estimator,
  treatedGeoAssignments,
  controlGeoAssignments,
  geoCoordinates,
  geoOutcomeKind,
  mediaChannels,
  controlColumns,
  aggregateSpendColumn,
  mappedOutcomeColumn,
  mmmSeasonalityPeriod,
  mmmOutcomeKind,
  mmmAdstockDecay,
  mmmSaturationHalfSpend,
  rewardColumn,
  expectedRewardColumn,
  primaryMethod,
  onGeoOutcomeKindChange,
  onGeoCoordinateChange,
  onMmmSeasonalityPeriodChange,
  onMmmAdstockDecayChange,
  onMmmSaturationHalfSpendChange,
  onRewardColumnChange,
  onExpectedRewardColumnChange,
  onPrimaryMethodChange,
  onContinue,
}: AnalysisEstimatorSettingsStepProps) {
  const numericColumns = preview.columns.filter(
    (column) =>
      column.inferred_type === "integer" || column.inferred_type === "float",
  );

  const assignedGeoValues = Array.from(
    new Set([...treatedGeoAssignments, ...controlGeoAssignments]),
  );

  const geoCoordinatesReady =
    assignedGeoValues.length > 0 &&
    assignedGeoValues.every(
      (value) => coordinateValidationMessage(geoCoordinates[value]) === null,
    );

  const verifiedCoordinateCount = assignedGeoValues.filter(
    (value) =>
      geoCoordinates[value]?.source === "dataset" &&
      coordinateValidationMessage(geoCoordinates[value]) === null,
  ).length;

  const manualCoordinateCount = assignedGeoValues.filter(
    (value) => geoCoordinates[value]?.source === "manual",
  ).length;

  const invalidCoordinateCount = assignedGeoValues.filter(
    (value) => coordinateValidationMessage(geoCoordinates[value]) !== null,
  ).length;

  const seasonalityPeriod = Number(mmmSeasonalityPeriod);

  const mmmReady =
    mediaChannels.length > 0
    && Number.isInteger(seasonalityPeriod)
    && seasonalityPeriod > 1;

  const offPolicySettingsReady =
    rewardColumn.length > 0 && expectedRewardColumn.length > 0;

  const canContinue =
    estimator === "difference_in_differences" ||
    estimator === "synthetic_control" ||
    (estimator === "geo_holdout" && geoCoordinatesReady) ||
    (estimator === "marketing_mix_model" && mmmReady) ||
    (estimator === "off_policy_evaluation" && offPolicySettingsReady);

  const readinessMessage =
    estimator === "difference_in_differences"
      ? "No additional estimator settings are required. did-v1 uses an unadjusted Difference in Differences specification; mapped covariates are preserved for lineage but are not included in estimation."
      : estimator === "synthetic_control"
        ? "The treated unit and donor pool fully define this estimator."
        : estimator === "geo_holdout"
          ? geoCoordinatesReady
            ? `${assignedGeoValues.length} geography coordinates are ready.`
            : `${invalidCoordinateCount} geography coordinate ${
                invalidCoordinateCount === 1 ? "requires" : "require"
              } attention.`
          : estimator === "marketing_mix_model"
            ? mmmReady
              ? `${mediaChannels.length} media ${
                  mediaChannels.length === 1 ? "channel is" : "channels are"
                } configured.`
              : mediaChannels.length === 0
                ? "No channel-level spend columns were detected."
                : "Enter a seasonality period greater than one."
            : offPolicySettingsReady
              ? "Reward columns and evaluation method are ready."
              : "Select both reward columns before continuing.";

  return (
    <main className="analysis-settings-shell">
      <header className="analysis-settings-hero">
        <p className="analysis-settings-hero__eyebrow">
          Estimator configuration
        </p>

        <h1>Configure Analysis</h1>

        <p>
          Finalize the method-specific inputs used to estimate and validate the
          incremental effect.
        </p>
      </header>

      <section
        className="analysis-settings-card"
        aria-labelledby={"estimator-settings-heading"}
      >
        <header className="analysis-settings-card__header">
          <span className="analysis-settings-card__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M10 14v6"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </span>

          <span>
            <h2 id={"estimator-settings-heading"}>Estimator settings</h2>

            <p>{estimatorTitle(estimator)}</p>
          </span>

          <span className="analysis-settings-status" data-ready={canContinue}>
            <span aria-hidden="true">{canContinue ? "✓" : "!"}</span>

            {canContinue ? "Ready" : "Incomplete"}
          </span>
        </header>

        {estimator === "difference_in_differences" && (
          <div className="analysis-settings-content">
            <article className="analysis-settings-complete">
              <span
                className="analysis-settings-complete__icon"
                aria-hidden="true"
              >
                ✓
              </span>

              <span>
                <h3>Configuration already complete</h3>

                <p>
                  No additional estimator settings are required for Difference
                  in Differences.
                </p>

                <small>
                  did-v1 estimates outcome ~ treated + post + treated:post
                  with standard errors clustered by unit. Mapped covariates are
                  preserved for lineage but are not included in this estimator.
                </small>
              </span>
            </article>
          </div>
        )}

        {estimator === "synthetic_control" && (
          <div className="analysis-settings-content">
            <article className="analysis-settings-complete">
              <span
                className="analysis-settings-complete__icon"
                aria-hidden="true"
              >
                ✓
              </span>

              <span>
                <h3>Donor design already complete</h3>

                <p>
                  The treated unit and donor pool define this Synthetic Control
                  analysis.
                </p>

                <small>
                  The estimator will optimize donor weights using the configured
                  pre-intervention period.
                </small>
              </span>
            </article>
          </div>
        )}

        {estimator === "geo_holdout" && (
          <div className="analysis-settings-content">
            <div className="analysis-settings-summary">
              <span>
                <strong>{assignedGeoValues.length}</strong>

                <small>Assigned geographies</small>
              </span>

              <span data-tone="verified">
                <strong>{verifiedCoordinateCount}</strong>

                <small>Dataset verified</small>
              </span>

              <span data-tone="manual">
                <strong>{manualCoordinateCount}</strong>

                <small>Manual entries</small>
              </span>

              <span
                data-tone={invalidCoordinateCount > 0 ? "warning" : "ready"}
              >
                <strong>{invalidCoordinateCount}</strong>

                <small>Need attention</small>
              </span>
            </div>

            <div className="analysis-settings-guidance">
              <span aria-hidden="true">i</span>

              <p>
                <strong>
                  Coordinates are used for geography-aware holdout estimation.
                </strong>

                <small>
                  Verified dataset coordinates remain read-only. Missing
                  coordinates must be entered manually before continuing.
                </small>
              </p>
            </div>

            <label className="analysis-settings-primary-field">
              <span>
                <strong>Geo outcome kind</strong>

                <small>
                  Select the business outcome represented by the mapped outcome
                  column.
                </small>
              </span>

              <select
                aria-label="Geo outcome kind"
                value={geoOutcomeKind}
                onChange={(event) => {
                  onGeoOutcomeKindChange(event.target.value);
                }}
              >
                <option value="outcome">Outcome</option>

                <option value="revenue">Revenue</option>

                <option value="conversions">Conversions</option>
              </select>
            </label>

            <div className="analysis-coordinate-grid">
              {assignedGeoValues.map((value) => {
                const coordinate = geoCoordinates[value] ?? {
                  latitude: "",
                  longitude: "",
                  source: "manual" as const,
                };

                const validationMessage =
                  coordinateValidationMessage(coordinate);

                const assignment = treatedGeoAssignments.includes(value)
                  ? "Treated"
                  : "Control";

                return (
                  <fieldset
                    className="analysis-coordinate-card"
                    data-valid={validationMessage === null}
                    key={value}
                  >
                    <legend>
                      <span>
                        <strong>{value}</strong>

                        <small>{assignment}</small>
                      </span>

                      <span
                        className="analysis-coordinate-card__status"
                        data-source={coordinate.source}
                      >
                        {coordinate.source === "dataset"
                          ? "Verified dataset coordinate"
                          : "Manual coordinate required"}
                      </span>
                    </legend>

                    <div className="analysis-coordinate-fields">
                      <label>
                        <span>Latitude</span>

                        <input
                          type="number"
                          step="any"
                          aria-label={`Latitude ${value}`}
                          value={coordinate.latitude}
                          readOnly={coordinate.source === "dataset"}
                          onChange={(event) => {
                            onGeoCoordinateChange(
                              value,
                              "latitude",
                              event.target.value,
                            );
                          }}
                        />
                      </label>

                      <label>
                        <span>Longitude</span>

                        <input
                          type="number"
                          step="any"
                          aria-label={`Longitude ${value}`}
                          value={coordinate.longitude}
                          readOnly={coordinate.source === "dataset"}
                          onChange={(event) => {
                            onGeoCoordinateChange(
                              value,
                              "longitude",
                              event.target.value,
                            );
                          }}
                        />
                      </label>
                    </div>

                    {validationMessage !== null && (
                      <p className="analysis-coordinate-error" role="alert">
                        {validationMessage}
                      </p>
                    )}
                  </fieldset>
                );
              })}
            </div>
          </div>
        )}

        {estimator === "marketing_mix_model" && (
          <div className="analysis-settings-content">
            <div className="analysis-settings-summary">
              <span>
                <strong>{mediaChannels.length}</strong>

                <small>Media channels</small>
              </span>

              <span>
                <strong>{mmmSeasonalityPeriod || "—"}</strong>

                <small>Seasonality period</small>
              </span>

              <span>
                <strong>{mmmOutcomeKind}</strong>

                <small>Outcome kind</small>
              </span>
            </div>

            <div className="analysis-settings-guidance">
              <span aria-hidden="true">i</span>

              <p>
                <strong>
                  Configure carryover and saturation for each media channel.
                </strong>

                <small>
                  Adstock represents delayed channel effects. Half-spend
                  controls where response begins to saturate.
                </small>
              </p>
            </div>

            <div className="analysis-mmm-primary-grid">
              <label className="analysis-settings-primary-field">
                <span>
                  <strong>Seasonality period</strong>

                  <small>
                    Number of observations in one complete seasonal cycle.
                  </small>
                </span>

                <input
                  type="number"
                  min="2"
                  step="1"
                  aria-label="Seasonality period"
                  value={mmmSeasonalityPeriod}
                  onChange={(event) => {
                    onMmmSeasonalityPeriodChange(event.target.value);
                  }}
                />
              </label>

              <label className="analysis-settings-primary-field">
                <span>
                  <strong>MMM outcome kind</strong>

                  <small>
                    Derived from mapped outcome “{mappedOutcomeColumn}”.
                  </small>
                </span>

                <input
                  type="text"
                  aria-label="MMM outcome kind"
                  value={mmmOutcomeKind}
                  readOnly
                />
              </label>
            </div>

            <dl className="analysis-mmm-role-summary">
              <div>
                <dt>Aggregate spend</dt>
                <dd>{aggregateSpendColumn ?? "Not mapped"}</dd>
              </div>

              <div>
                <dt>Control variables</dt>
                <dd>
                  {controlColumns.length > 0
                    ? controlColumns.join(", ")
                    : "None mapped"}
                </dd>
              </div>
            </dl>

            <div className="analysis-mmm-channel-grid">
              {mediaChannels.map((channel) => (
                <fieldset className="analysis-mmm-channel-card" key={channel}>
                  <legend>
                    <span aria-hidden="true">↗</span>

                    <span>
                      <strong>{channel}</strong>

                      <small>Media response settings</small>
                    </span>
                  </legend>

                  <label>
                    <span>
                      <strong>Adstock decay</strong>

                      <small>Retained effect from previous periods.</small>
                    </span>

                    <input
                      type="number"
                      step="any"
                      aria-label={`Adstock decay ${channel}`}
                      value={mmmAdstockDecay[channel] ?? "0.5"}
                      onChange={(event) => {
                        onMmmAdstockDecayChange(channel, event.target.value);
                      }}
                    />
                  </label>

                  <label>
                    <span>
                      <strong>Saturation half-spend</strong>

                      <small>
                        Spend level reaching half the maximum response.
                      </small>
                    </span>

                    <input
                      type="number"
                      step="any"
                      aria-label={`Saturation half-spend ${channel}`}
                      value={mmmSaturationHalfSpend[channel] ?? "1"}
                      onChange={(event) => {
                        onMmmSaturationHalfSpendChange(
                          channel,
                          event.target.value,
                        );
                      }}
                    />
                  </label>
                </fieldset>
              ))}
            </div>
          </div>
        )}

        {estimator === "off_policy_evaluation" && (
          <div className="analysis-settings-content">
            <div className="analysis-settings-guidance">
              <span aria-hidden="true">i</span>

              <p>
                <strong>Select observed and modeled reward signals.</strong>

                <small>
                  The primary method determines how logged propensities and
                  expected rewards are combined.
                </small>
              </p>
            </div>

            <div className="analysis-policy-settings-grid">
              <label className="analysis-settings-primary-field">
                <span>
                  <strong>Reward column</strong>

                  <small>Observed reward generated by the logged action.</small>
                </span>

                <select
                  aria-label="Reward column"
                  value={rewardColumn}
                  onChange={(event) => {
                    onRewardColumnChange(event.target.value);
                  }}
                >
                  <option value="">Choose reward column</option>

                  {numericColumns.map((column) => (
                    <option key={column.name} value={column.name}>
                      {column.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="analysis-settings-primary-field">
                <span>
                  <strong>Expected reward column</strong>

                  <small>
                    Modeled reward used by doubly robust estimation.
                  </small>
                </span>

                <select
                  aria-label="Expected reward column"
                  value={expectedRewardColumn}
                  onChange={(event) => {
                    onExpectedRewardColumnChange(event.target.value);
                  }}
                >
                  <option value="">Choose expected reward column</option>

                  {numericColumns.map((column) => (
                    <option key={column.name} value={column.name}>
                      {column.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="analysis-settings-primary-field">
                <span>
                  <strong>Primary method</strong>

                  <small>
                    Main estimator used for the reported policy value.
                  </small>
                </span>

                <select
                  aria-label="Primary method"
                  value={primaryMethod}
                  onChange={(event) => {
                    onPrimaryMethodChange(
                      event.target.value as OffPolicyMethod,
                    );
                  }}
                >
                  <option value="importance_sampling">
                    Importance sampling
                  </option>

                  <option value="self_normalized_importance_sampling">
                    Self-normalized importance sampling
                  </option>

                  <option value="doubly_robust">Doubly robust</option>
                </select>
              </label>
            </div>
          </div>
        )}

        <footer className="analysis-settings-actions">
          <span data-ready={canContinue}>
            <strong>
              {canContinue ? "Ready for review" : "Settings incomplete"}
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
