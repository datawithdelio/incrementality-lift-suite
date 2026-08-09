import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalysisEstimatorSettingsStep } from "../src/components/analysis-configuration/analysis-estimator-settings-step";

const preview = {
  dataset_id: "dataset-1",
  page: 1,
  page_size: 50,
  total_rows: 2,
  total_pages: 1,
  columns: [],
  rows: [],
  date_range: null,
  treatment_distribution: {},
  outcome_distribution: {},
};

function renderGeoSettings(
  coordinates: Record<
    string,
    {
      latitude: string;
      longitude: string;
      source: "dataset" | "manual";
    }
  >,
  onGeoCoordinateChange = vi.fn(),
) {
  render(
    <AnalysisEstimatorSettingsStep
      preview={preview}
      estimator="geo_holdout"
      treatedGeoAssignments={["Boston"]}
      controlGeoAssignments={["Chicago"]}
      geoCoordinates={coordinates}
      geoOutcomeKind="outcome"
      mediaChannels={[]}
      controlColumns={[]}
      aggregateSpendColumn="total_spend"
      mappedOutcomeColumn="revenue"
      mmmSeasonalityPeriod="52"
      mmmOutcomeKind="revenue"
      mmmAdstockDecay={{}}
      mmmSaturationHalfSpend={{}}
      rewardColumn=""
      expectedRewardColumn=""
      primaryMethod="doubly_robust"
      onGeoOutcomeKindChange={vi.fn()}
      onGeoCoordinateChange={onGeoCoordinateChange}
      onMmmSeasonalityPeriodChange={vi.fn()}
      onMmmAdstockDecayChange={vi.fn()}
      onMmmSaturationHalfSpendChange={vi.fn()}
      onRewardColumnChange={vi.fn()}
      onExpectedRewardColumnChange={vi.fn()}
      onPrimaryMethodChange={vi.fn()}
      onContinue={vi.fn()}
    />,
  );
}

afterEach(() => {
  cleanup();
});

describe("Geo Holdout coordinate workflow", () => {
  it("shows verified dataset coordinates as read-only", () => {
    renderGeoSettings({
      Boston: {
        latitude: "42.3601",
        longitude: "-71.0589",
        source: "dataset",
      },
      Chicago: {
        latitude: "41.8781",
        longitude: "-87.6298",
        source: "dataset",
      },
    });

    expect(screen.getByLabelText("Latitude Boston")).toHaveValue(42.3601);

    expect(screen.getByLabelText("Latitude Boston")).toHaveAttribute(
      "readonly",
    );

    expect(screen.getAllByText("Verified dataset coordinate")).toHaveLength(2);

    expect(
      screen.getByRole("button", {
        name: "Continue",
      }),
    ).toBeEnabled();
  });

  it("requires valid manual coordinates before continuing", () => {
    const onGeoCoordinateChange = vi.fn();

    renderGeoSettings(
      {
        Boston: {
          latitude: "42.3601",
          longitude: "-71.0589",
          source: "dataset",
        },
        Chicago: {
          latitude: "95",
          longitude: "",
          source: "manual",
        },
      },
      onGeoCoordinateChange,
    );

    expect(
      screen.getByText("Latitude must be a number between -90 and 90."),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Continue",
      }),
    ).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Latitude Chicago"), {
      target: {
        value: "41.8781",
      },
    });

    expect(onGeoCoordinateChange).toHaveBeenCalledWith(
      "Chicago",
      "latitude",
      "41.8781",
    );
  });
});
