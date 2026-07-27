import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalysisTreatmentControlStep } from "../src/components/analysis-configuration/analysis-treatment-control-step";

import type {
  DatasetPreview,
  GeographySummary,
} from "../src/lib/data-products/types";

const preview: DatasetPreview = {
  rows: [
    {
      geography: "Boston",
      outcome: 100,
      spend: 20,
    },
    {
      geography: "Chicago",
      outcome: 90,
      spend: 18,
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
      name: "outcome",
      inferred_type: "float",
      missing_percentage: 0,
      unique_count: 2,
      minimum: 90,
      maximum: 100,
      mean: 95,
      median: 95,
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
  ],
  total_rows: 2,
  page: 1,
  page_size: 50,
  total_pages: 1,
  date_range: null,
  treatment_distribution: {},
  outcome_distribution: {},
};

const geographySummary: GeographySummary = {
  mapping_version: 3,
  unit_column: "geography",
  total_geographies: 3,
  geographies: [
    {
      value: "Boston",
      observation_count: 120,
      latitude: 42.3601,
      longitude: -71.0589,
      coordinate_status: "verified",
      metrics: {
        outcome_sum: 1200,
        spend_sum: 250,
        covariate_sums: {},
      },
    },
    {
      value: "Chicago",
      observation_count: 115,
      latitude: 41.8781,
      longitude: -87.6298,
      coordinate_status: "verified",
      metrics: {
        outcome_sum: 1100,
        spend_sum: 230,
        covariate_sums: {},
      },
    },
    {
      value: "New York",
      observation_count: 118,
      latitude: null,
      longitude: null,
      coordinate_status: "missing",
      metrics: {
        outcome_sum: 1250,
        spend_sum: 270,
        covariate_sums: {},
      },
    },
  ],
};

function renderGeoHoldout(
  treatedGeoAssignments: string[] = [],
  controlGeoAssignments: string[] = [],
) {
  const onTreatedGeoChange = vi.fn();
  const onControlGeoChange = vi.fn();

  render(
    <AnalysisTreatmentControlStep
      preview={preview}
      geographySummary={geographySummary}
      estimator="geo_holdout"
      unitColumn="geography"
      treatmentColumn="treated"
      treatmentValue="1"
      controlValue="0"
      treatedUnit=""
      donorPool={[]}
      treatedGeoAssignments={treatedGeoAssignments}
      controlGeoAssignments={controlGeoAssignments}
      policyName=""
      behaviorPropensityColumn=""
      targetPropensityColumn=""
      onTreatedUnitChange={vi.fn()}
      onDonorChange={vi.fn()}
      onTreatedGeoChange={onTreatedGeoChange}
      onControlGeoChange={onControlGeoChange}
      onPolicyNameChange={vi.fn()}
      onBehaviorPropensityColumnChange={vi.fn()}
      onTargetPropensityColumnChange={vi.fn()}
      onContinue={vi.fn()}
    />,
  );

  return {
    onTreatedGeoChange,
    onControlGeoChange,
  };
}

afterEach(() => {
  cleanup();
});

describe("premium treatment and control setup", () => {
  it("uses the complete geography summary rather than preview-only values", () => {
    renderGeoHoldout();

    expect(
      screen.getByRole("heading", {
        name: "Treatment and control setup",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Treat geography New York"),
    ).toBeInTheDocument();

    expect(screen.getByText("Coordinates required")).toBeInTheDocument();

    expect(screen.getByText("120")).toBeInTheDocument();
  });

  it("shows assignment counts and preserves callbacks", () => {
    const { onTreatedGeoChange, onControlGeoChange } = renderGeoHoldout(
      ["Boston"],
      ["Chicago"],
    );

    expect(
      screen.getByRole("button", {
        name: "Continue",
      }),
    ).toBeEnabled();

    expect(
      screen.getByText("1 treated and 1 control geographies assigned."),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Treat geography Boston"));

    expect(onTreatedGeoChange).toHaveBeenCalledWith("Boston", false);

    fireEvent.click(screen.getByLabelText("Control geography Chicago"));

    expect(onControlGeoChange).toHaveBeenCalledWith("Chicago", false);
  });
});
