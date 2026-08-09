import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { ComponentProps } from "react";

import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalysisEstimatorSettingsStep } from "../src/components/analysis-configuration/analysis-estimator-settings-step";

import type { DatasetPreview } from "../src/lib/data-products/types";

const preview: DatasetPreview = {
  page: 1,
  page_size: 50,
  total_rows: 2,
  total_pages: 1,
  rows: [
    {
      geography: "Boston",
      spend: 20,
      revenue: 100,
    },
    {
      geography: "Chicago",
      spend: 18,
      revenue: 90,
    },
  ],
  columns: [
    {
      name: "geography",
      inferred_type: "string",
      missing_percentage: 0,
      unique_count: 2,
      minimum: null,
      maximum: null,
      mean: null,
      median: null,
    },
    {
      name: "spend",
      inferred_type: "float",
      missing_percentage: 0,
      unique_count: 2,
      minimum: 18,
      maximum: 20,
      mean: 19,
      median: 19,
    },
    {
      name: "revenue",
      inferred_type: "float",
      missing_percentage: 0,
      unique_count: 2,
      minimum: 90,
      maximum: 100,
      mean: 95,
      median: 95,
    },
  ],
  date_range: null,
  treatment_distribution: {},
  outcome_distribution: {},
};

type SettingsProps = ComponentProps<typeof AnalysisEstimatorSettingsStep>;

function createProps(): SettingsProps {
  return {
    preview,
    estimator: "difference_in_differences",
    treatedGeoAssignments: [],
    controlGeoAssignments: [],
    geoCoordinates: {},
    geoOutcomeKind: "outcome",
    mediaChannels: [],
    controlColumns: [],
    aggregateSpendColumn: "total_spend",
    mappedOutcomeColumn: "revenue",
    mmmSeasonalityPeriod: "52",
    mmmOutcomeKind: "revenue",
    mmmAdstockDecay: {},
    mmmSaturationHalfSpend: {},
    rewardColumn: "",
    expectedRewardColumn: "",
    primaryMethod: "doubly_robust",
    onGeoOutcomeKindChange: vi.fn(),
    onGeoCoordinateChange: vi.fn(),
    onMmmSeasonalityPeriodChange: vi.fn(),
    onMmmAdstockDecayChange: vi.fn(),
    onMmmSaturationHalfSpendChange: vi.fn(),
    onRewardColumnChange: vi.fn(),
    onExpectedRewardColumnChange: vi.fn(),
    onPrimaryMethodChange: vi.fn(),
    onContinue: vi.fn(),
  };
}

function renderSettings(overrides: Partial<SettingsProps> = {}): SettingsProps {
  const props = {
    ...createProps(),
    ...overrides,
  };

  render(<AnalysisEstimatorSettingsStep {...props} />);

  return props;
}

afterEach(() => {
  cleanup();
});

describe("premium estimator settings", () => {
  it("summarizes verified and manual Geo Holdout coordinates", () => {
    const props = renderSettings({
      estimator: "geo_holdout",
      treatedGeoAssignments: ["Boston"],
      controlGeoAssignments: ["Chicago"],
      geoCoordinates: {
        Boston: {
          latitude: "42.3601",
          longitude: "-71.0589",
          source: "dataset",
        },
        Chicago: {
          latitude: "41.8781",
          longitude: "-87.6298",
          source: "manual",
        },
      },
    });

    expect(
      screen.getByRole("heading", {
        name: "Estimator settings",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("Verified dataset coordinate")).toBeInTheDocument();

    expect(screen.getByText("Manual coordinate required")).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Continue",
      }),
    ).toBeEnabled();

    fireEvent.change(screen.getByLabelText("Geo outcome kind"), {
      target: {
        value: "revenue",
      },
    });

    expect(props.onGeoOutcomeKindChange).toHaveBeenCalledWith("revenue");
  });

  it("presents channel-level Marketing Mix settings", () => {
    const props = renderSettings({
      estimator: "marketing_mix_model",
      mediaChannels: ["paid_search_spend", "social_spend"],
      controlColumns: ["sessions", "holiday", "promotion"],
      aggregateSpendColumn: "total_spend",
      mappedOutcomeColumn: "conversions",
      mmmOutcomeKind: "conversions",
    });

    expect(screen.getByLabelText("Seasonality period")).toHaveValue(52);

    expect(screen.getByLabelText("MMM outcome kind")).toHaveValue(
      "conversions",
    );
    expect(screen.getByLabelText("MMM outcome kind")).toHaveAttribute(
      "readonly",
    );
    expect(screen.getByLabelText("Adstock decay paid_search_spend")).toHaveValue(0.5);

    expect(screen.getByLabelText("Saturation half-spend social_spend")).toHaveValue(
      1,
    );

    fireEvent.change(screen.getByLabelText("Adstock decay paid_search_spend"), {
      target: {
        value: "0.7",
      },
    });

    expect(props.onMmmAdstockDecayChange).toHaveBeenCalledWith(
      "paid_search_spend",
      "0.7",
    );
  });

  it("shows Off-policy readiness from the configured reward columns", () => {
    renderSettings({
      estimator: "off_policy_evaluation",
      rewardColumn: "revenue",
      expectedRewardColumn: "spend",
      primaryMethod: "doubly_robust",
    });

    expect(screen.getByLabelText("Primary method")).toHaveValue(
      "doubly_robust",
    );

    expect(
      screen.getByText("Reward columns and evaluation method are ready."),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Continue",
      }),
    ).toBeEnabled();
  });
});
