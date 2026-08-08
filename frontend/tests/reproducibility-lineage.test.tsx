import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReproducibilityExperience } from "../src/components/results/reproducibility-experience";

const lineage = {
  analysis_run_id: "run-1",
  dataset_id: "dataset-1",
  dataset_checksum_sha256: "b".repeat(64),
  dataset_byte_size: 4096,
  semantic_mapping_id: "mapping-1",
  semantic_mapping_version: 3,
  semantic_mapping_snapshot: {
    outcome_column: "revenue",
    treatment_column: "treated",
  },
  analysis_period_snapshot: {
    analysis_start_date: "2026-01-01",
    analysis_end_date: "2026-01-31",
  },
  analysis_selection_snapshot: {
    selected_geographies: ["Boston"],
  },
  treatment_control_snapshot: {
    treated_units: ["Boston"],
    control_units: ["Chicago"],
  },
  estimand_snapshot: {
    estimator_type: "difference_in_differences",
    estimand_type: "average_differential_change",
    target_outcome: "revenue",
    target_population: "treated units in the post-treatment period",
    treated_population: "yes",
    comparison: "control group counterfactual change",
    effect_scale: "absolute_outcome_units",
    aggregation_method: "difference_in_differences_interaction_coefficient",
    analysis_time_scope: "post_treatment_period",
    unit_of_analysis: "unit_period",
    policy_target: null,
  },
  estimator_type: "difference_in_differences",
  estimator_version: "did-v2",
  estimator_configuration: {
    intervention_time: "2026-01-01",
  },
  random_seed: 1729,
  application_version: "0.1.0",
  source_revision: "c".repeat(40),
  statistical_library_versions: {
    numpy: "2.3.1",
    statsmodels: "0.14.5",
  },
  input_fingerprint_sha256: "a".repeat(64),
  created_at: "2026-07-17T20:00:00Z",
};

afterEach(cleanup);

describe("ReproducibilityExperience", () => {
  it("labels persisted run timestamps as UTC", () => {
    render(
      <ReproducibilityExperience
        state={{ kind: "ready", data: lineage }}
      />,
    );

    expect(screen.getAllByText("Jul 17, 2026, 8:00 PM UTC")).toHaveLength(2);
  });

  it("shows a focused loading state", () => {
    render(
      <ReproducibilityExperience
        state={{ kind: "loading" }}
      />,
    );

    expect(
      screen.getByText("Loading reproducibility lineage"),
    ).toBeInTheDocument();
  });

  it("shows a safe error state", () => {
    render(
      <ReproducibilityExperience
        state={{ kind: "error" }}
      />,
    );

    expect(
      screen.getByText(
        "Reproducibility details are temporarily unavailable",
      ),
    ).toBeInTheDocument();
  });

  it("clearly labels historical runs with incomplete lineage", () => {
    render(
      <ReproducibilityExperience
        state={{
          kind: "ready",
          data: {
            ...lineage,
            semantic_mapping_snapshot: null,
            analysis_period_snapshot: null,
            analysis_selection_snapshot: null,
            treatment_control_snapshot: null,
            estimand_snapshot: null,
          },
        }}
      />,
    );

    expect(
      screen.getByText("Legacy run"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Some lineage fields are unavailable for this historical run.",
      ),
    ).toBeInTheDocument();
  });

  it("shows the complete persisted reproducibility receipt", () => {
    render(
      <ReproducibilityExperience
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
      screen.getAllByText(
        "difference_in_differences",
      ).length,
    ).toBeGreaterThan(0);

    expect(
      screen.getByText("did-v2"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("1729"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("0.1.0"),
    ).toBeInTheDocument();

    expect(
      screen.getAllByText(
        "average_differential_change",
      ).length,
    ).toBeGreaterThan(0);

    expect(
      screen.getByText("statsmodels 0.14.5"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("a".repeat(64)),
    ).toBeInTheDocument();

    expect(
      screen.getByText("b".repeat(64)),
    ).toBeInTheDocument();

    expect(
      screen.getByText("c".repeat(40)),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("textbox"),
    ).not.toBeInTheDocument();
  });

  it("can copy the persisted input fingerprint", () => {
    const writeText = vi.fn();

    Object.defineProperty(
      navigator,
      "clipboard",
      {
        configurable: true,
        value: {
          writeText,
        },
      },
    );

    render(
      <ReproducibilityExperience
        state={{
          kind: "ready",
          data: lineage,
        }}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Copy input fingerprint",
      }),
    );

    expect(writeText).toHaveBeenCalledWith(
      "a".repeat(64),
    );
  });


  it("copies the exact persisted dataset checksum and source revision", () => {
    const writeText = vi.fn();

    Object.defineProperty(
      navigator,
      "clipboard",
      {
        configurable: true,
        value: {
          writeText,
        },
      },
    );

    render(
      <ReproducibilityExperience
        state={{
          kind: "ready",
          data: lineage,
        }}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Copy dataset checksum",
      }),
    );

    expect(writeText).toHaveBeenLastCalledWith(
      "b".repeat(64),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Copy source revision",
      }),
    );

    expect(writeText).toHaveBeenLastCalledWith(
      "c".repeat(40),
    );
  });



  it("links back to the exact analysis run status", () => {
    render(
      <ReproducibilityExperience
        workspaceId="workspace-1"
        projectId="project-1"
        analysisRunId="run-1"
        state={{
          kind: "ready",
          data: lineage,
        }}
      />,
    );

    expect(
      screen.getByRole("link", {
        name: "View Analysis Status",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1",
    );
  });



  it("links completed runs to exact Results and Reports destinations", () => {
    render(
      <ReproducibilityExperience
        workspaceId="workspace-1"
        projectId="project-1"
        analysisRunId="run-1"
        resultAvailable
        reportsAvailable
        state={{
          kind: "ready",
          data: lineage,
        }}
      />,
    );

    expect(
      screen.getByRole("link", {
        name: "View Results",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1/result",
    );

    expect(
      screen.getByRole("link", {
        name: "View Reports",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1/reports",
    );
  });


  it("does not expose unavailable Results or Reports destinations", () => {
    render(
      <ReproducibilityExperience
        workspaceId="workspace-1"
        projectId="project-1"
        analysisRunId="run-1"
        resultAvailable={false}
        reportsAvailable={false}
        state={{
          kind: "ready",
          data: lineage,
        }}
      />,
    );

    expect(
      screen.getByRole("link", {
        name: "View Analysis Status",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1",
    );

    expect(
      screen.queryByRole("link", {
        name: "View Results",
      }),
    ).not.toBeInTheDocument();

    expect(
      screen.queryByRole("link", {
        name: "View Reports",
      }),
    ).not.toBeInTheDocument();
  });



  it("states the supported reproducibility boundary", () => {
    render(
      <ReproducibilityExperience
        state={{
          kind: "ready",
          data: lineage,
        }}
      />,
    );

    expect(
      screen.getByText(
        /does not guarantee bit-for-bit identical results across different hardware/i,
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /operating systems or numerical backends/i,
      ),
    ).toBeInTheDocument();
  });

});
