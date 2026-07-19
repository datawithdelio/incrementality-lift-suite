import type {
  AnalysisEstimatorType,
  OffPolicyMethod,
} from "@/lib/analysis-configuration/request";

import type {
  DatasetPreview,
} from "@/lib/data-products/types";

type GeoCoordinateDraft = {
  latitude: string;
  longitude: string;
};

type AnalysisEstimatorSettingsStepProps = {
  preview: DatasetPreview;

  estimator:
    AnalysisEstimatorType;

  treatedGeoAssignments:
    string[];

  controlGeoAssignments:
    string[];

  geoCoordinates:
    Record<
      string,
      GeoCoordinateDraft
    >;

  geoOutcomeKind: string;

  spendColumn:
    string | null;

  covariateColumns:
    string[];

  mmmSeasonalityPeriod:
    string;

  mmmOutcomeKind:
    string;

  mmmAdstockDecay:
    Record<string, string>;

  mmmSaturationHalfSpend:
    Record<string, string>;

  rewardColumn:
    string;

  expectedRewardColumn:
    string;

  primaryMethod:
    OffPolicyMethod;

  onGeoOutcomeKindChange: (
    value: string,
  ) => void;

  onGeoCoordinateChange: (
    geography: string,
    field:
      | "latitude"
      | "longitude",
    value: string,
  ) => void;

  onMmmSeasonalityPeriodChange: (
    value: string,
  ) => void;

  onMmmOutcomeKindChange: (
    value: string,
  ) => void;

  onMmmAdstockDecayChange: (
    channel: string,
    value: string,
  ) => void;

  onMmmSaturationHalfSpendChange: (
    channel: string,
    value: string,
  ) => void;

  onRewardColumnChange: (
    value: string,
  ) => void;

  onExpectedRewardColumnChange: (
    value: string,
  ) => void;

  onPrimaryMethodChange: (
    value: OffPolicyMethod,
  ) => void;

  onContinue: () => void;
};

export function AnalysisEstimatorSettingsStep({
  preview,
  estimator,
  treatedGeoAssignments,
  controlGeoAssignments,
  geoCoordinates,
  geoOutcomeKind,
  spendColumn,
  covariateColumns,
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
  onMmmOutcomeKindChange,
  onMmmAdstockDecayChange,
  onMmmSaturationHalfSpendChange,
  onRewardColumnChange,
  onExpectedRewardColumnChange,
  onPrimaryMethodChange,
  onContinue,
}: AnalysisEstimatorSettingsStepProps) {
  const numericColumns =
    preview.columns.filter(
      (column) =>
        column.inferred_type
          === "integer"
        || column.inferred_type
          === "float",
    );

  const assignedGeoValues =
    Array.from(
      new Set([
        ...treatedGeoAssignments,
        ...controlGeoAssignments,
      ]),
    );

  const geoCoordinatesReady =
    assignedGeoValues.length > 0
    && assignedGeoValues.every(
      (value) => {
        const coordinate =
          geoCoordinates[value];

        if (
          coordinate === undefined
          || coordinate.latitude
            .trim()
            .length === 0
          || coordinate.longitude
            .trim()
            .length === 0
        ) {
          return false;
        }

        const latitude =
          Number(
            coordinate.latitude,
          );

        const longitude =
          Number(
            coordinate.longitude,
          );

        return (
          Number.isFinite(
            latitude,
          )
          && Number.isFinite(
            longitude,
          )
          && latitude >= -90
          && latitude <= 90
          && longitude >= -180
          && longitude <= 180
        );
      },
    );

  const mmmChannels =
    Array.from(
      new Set(
        [
          spendColumn,
          ...covariateColumns,
        ].filter(
          (
            value,
          ): value is string =>
            typeof value
              === "string"
            && value.length > 0,
        ),
      ),
    );

  const seasonalityPeriod =
    Number(
      mmmSeasonalityPeriod,
    );

  const mmmReady =
    Number.isInteger(
      seasonalityPeriod,
    )
    && seasonalityPeriod > 1;

  const offPolicySettingsReady =
    rewardColumn.length > 0
    && expectedRewardColumn
      .length > 0;

  return (
    <main>
      <h1>
        Configure Analysis
      </h1>

      <section
        aria-labelledby={
          "estimator-settings-heading"
        }
      >
        <h2
          id={
            "estimator-settings-heading"
          }
        >
          Estimator settings
        </h2>

        {estimator
          === "difference_in_differences"
          && (
            <>
              <p>
                No additional estimator settings
                are required for Difference in
                Differences.
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
              <p>
                The treated unit and donor pool
                define this Synthetic Control
                analysis.
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
          === "geo_holdout"
          && (
            <>
              <label>
                <span>
                  Geo outcome kind
                </span>

                <select
                  aria-label={
                    "Geo outcome kind"
                  }
                  value={
                    geoOutcomeKind
                  }
                  onChange={(
                    event,
                  ) => {
                    onGeoOutcomeKindChange(
                      event.target
                        .value,
                    );
                  }}
                >
                  <option
                    value="outcome"
                  >
                    Outcome
                  </option>

                  <option
                    value="revenue"
                  >
                    Revenue
                  </option>

                  <option
                    value="conversions"
                  >
                    Conversions
                  </option>
                </select>
              </label>

              {assignedGeoValues.map(
                (value) => {
                  const coordinate =
                    geoCoordinates[
                      value
                    ]
                    ?? {
                      latitude: "",
                      longitude: "",
                    };

                  return (
                    <fieldset
                      key={value}
                    >
                      <legend>
                        {value}
                      </legend>

                      <label>
                        <span>
                          Latitude
                        </span>

                        <input
                          type="number"
                          step="any"
                          aria-label={
                            `Latitude ${value}`
                          }
                          value={
                            coordinate
                              .latitude
                          }
                          onChange={(
                            event,
                          ) => {
                            onGeoCoordinateChange(
                              value,
                              "latitude",
                              event.target
                                .value,
                            );
                          }}
                        />
                      </label>

                      <label>
                        <span>
                          Longitude
                        </span>

                        <input
                          type="number"
                          step="any"
                          aria-label={
                            `Longitude ${value}`
                          }
                          value={
                            coordinate
                              .longitude
                          }
                          onChange={(
                            event,
                          ) => {
                            onGeoCoordinateChange(
                              value,
                              "longitude",
                              event.target
                                .value,
                            );
                          }}
                        />
                      </label>
                    </fieldset>
                  );
                },
              )}

              <button
                type="button"
                disabled={
                  !geoCoordinatesReady
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
              <label>
                <span>
                  Seasonality period
                </span>

                <input
                  type="number"
                  min="2"
                  step="1"
                  aria-label={
                    "Seasonality period"
                  }
                  value={
                    mmmSeasonalityPeriod
                  }
                  onChange={(
                    event,
                  ) => {
                    onMmmSeasonalityPeriodChange(
                      event.target
                        .value,
                    );
                  }}
                />
              </label>

              <label>
                <span>
                  MMM outcome kind
                </span>

                <select
                  aria-label={
                    "MMM outcome kind"
                  }
                  value={
                    mmmOutcomeKind
                  }
                  onChange={(
                    event,
                  ) => {
                    onMmmOutcomeKindChange(
                      event.target
                        .value,
                    );
                  }}
                >
                  <option
                    value="revenue"
                  >
                    Revenue
                  </option>

                  <option
                    value="conversions"
                  >
                    Conversions
                  </option>

                  <option
                    value="outcome"
                  >
                    Outcome
                  </option>
                </select>
              </label>

              {mmmChannels.map(
                (channel) => (
                  <fieldset
                    key={channel}
                  >
                    <legend>
                      {channel}
                    </legend>

                    <label>
                      <span>
                        Adstock decay
                      </span>

                      <input
                        type="number"
                        step="any"
                        aria-label={
                          `Adstock decay ${channel}`
                        }
                        value={
                          mmmAdstockDecay[
                            channel
                          ]
                          ?? "0.5"
                        }
                        onChange={(
                          event,
                        ) => {
                          onMmmAdstockDecayChange(
                            channel,
                            event.target
                              .value,
                          );
                        }}
                      />
                    </label>

                    <label>
                      <span>
                        Saturation half-spend
                      </span>

                      <input
                        type="number"
                        step="any"
                        aria-label={
                          `Saturation half-spend ${channel}`
                        }
                        value={
                          mmmSaturationHalfSpend[
                            channel
                          ]
                          ?? "1"
                        }
                        onChange={(
                          event,
                        ) => {
                          onMmmSaturationHalfSpendChange(
                            channel,
                            event.target
                              .value,
                          );
                        }}
                      />
                    </label>
                  </fieldset>
                ),
              )}

              <button
                type="button"
                disabled={
                  !mmmReady
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
          === "off_policy_evaluation"
          && (
            <>
              <label>
                <span>
                  Reward column
                </span>

                <select
                  aria-label={
                    "Reward column"
                  }
                  value={
                    rewardColumn
                  }
                  onChange={(
                    event,
                  ) => {
                    onRewardColumnChange(
                      event.target
                        .value,
                    );
                  }}
                >
                  <option value="">
                    Choose reward column
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
                  Expected reward column
                </span>

                <select
                  aria-label={
                    "Expected reward column"
                  }
                  value={
                    expectedRewardColumn
                  }
                  onChange={(
                    event,
                  ) => {
                    onExpectedRewardColumnChange(
                      event.target
                        .value,
                    );
                  }}
                >
                  <option value="">
                    Choose expected reward column
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
                  Primary method
                </span>

                <select
                  aria-label={
                    "Primary method"
                  }
                  value={
                    primaryMethod
                  }
                  onChange={(
                    event,
                  ) => {
                    onPrimaryMethodChange(
                      event.target.value as OffPolicyMethod,
                    );
                  }}
                >
                  <option
                    value={
                      "importance_sampling"
                    }
                  >
                    Importance sampling
                  </option>

                  <option
                    value={
                      "self_normalized_importance_sampling"
                    }
                  >
                    Self-normalized importance sampling
                  </option>

                  <option
                    value={
                      "doubly_robust"
                    }
                  >
                    Doubly robust
                  </option>
                </select>
              </label>

              <button
                type="button"
                disabled={
                  !offPolicySettingsReady
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
