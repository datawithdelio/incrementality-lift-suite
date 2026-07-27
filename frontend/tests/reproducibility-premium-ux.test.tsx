import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReproducibilityExperience } from "@/components/results/reproducibility-experience";
import type { AnalysisRunLineageResponse } from "@/lib/results/lineage-types";

const lineage: AnalysisRunLineageResponse = {
  analysis_run_id: "analysis-run-123",
  dataset_id: "dataset-456",
  dataset_checksum_sha256:
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  dataset_byte_size: 5242880,
  semantic_mapping_id: "mapping-789",
  semantic_mapping_version: 3,
  semantic_mapping_snapshot: {
    time_column: "date",
    unit_column: "market",
    treatment_column: "treated",
    outcome_column: "revenue",
    covariates: ["price", "seasonality"],
  },
  analysis_period_snapshot: {
    analysis_start_date: "2025-01-01",
    intervention_date: "2025-07-01",
    analysis_end_date: "2025-12-01",
  },
  analysis_selection_snapshot: {
    included_markets: 6,
    treated_markets: 3,
    control_markets: 3,
    row_filters: [],
  },
  treatment_control_snapshot: {
    assignment_rule: "mapped_binary_at_intervention",
    treatment_value: 1,
    control_value: 0,
    assignment_date: "2025-07-01",
  },
  estimand_snapshot: {
    estimand_type: "ATT",
    target_outcome: "revenue",
    target_population: "treated markets",
    effect_scale: "additive",
  },
  estimator_type: "difference_in_differences",
  estimator_version: "did-v1",
  estimator_configuration: {
    formula: "outcome ~ treated + post + treated:post",
  },
  random_seed: 4821,
  application_version: "1.0.0",
  source_revision: "97297f4",
  statistical_library_versions: {
    numpy: "2.4.6",
    statsmodels: "0.14.6",
  },
  input_fingerprint_sha256:
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  created_at: "2026-07-25T14:42:00Z",
};

describe("premium reproducibility experience", () => {
  it("renders the premium hierarchy using persisted lineage values", () => {
    render(
      <ReproducibilityExperience
        workspaceId="workspace-1"
        projectId="project-1"
        analysisRunId="analysis-run-123"
        resultAvailable
        reportsAvailable
        state={{
          kind: "ready",
          data: lineage,
        }}
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Reproducibility and lineage",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Execution identity",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Dataset lineage",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Analysis specification",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Runtime environment",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getAllByText("analysis-run-123").length,
    ).toBeGreaterThan(0);

    expect(
      screen.getByText("statsmodels 0.14.6"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "View Results",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/analysis-runs/analysis-run-123/result",
    );

    expect(
      screen.queryByText("practice.csv"),
    ).not.toBeInTheDocument();
  });

  it("marks historical runs with missing snapshots as legacy", () => {
    render(
      <ReproducibilityExperience
        state={{
          kind: "ready",
          data: {
            ...lineage,
            semantic_mapping_snapshot: null,
          },
        }}
      />,
    );

    expect(
      screen.getByText("Legacy run"),
    ).toBeInTheDocument();

    expect(
      screen.getAllByText(
        "Unavailable for this historical run.",
      ).length,
    ).toBeGreaterThan(0);
  });
});
