import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ResultsExperience } from "../src/components/results/results-experience";
import type { AnalysisResultResponse } from "../src/lib/results/types";

const base: AnalysisResultResponse = {
  analysis_run_id: "run-1",
  workspace_id: "workspace-1",
  project_id: "project-1",
  run_status: "succeeded",
  lifecycle_status: "succeeded",
  estimator_type: "difference_in_differences",
  estimator_version: "did-v2",
  analysis_configuration: { intervention_time: "2026-01-01" },
  attempt_count: 1,
  max_attempts: 3,
  failure_information: null,
  result: {
    effect_estimate: 8.2,
    standard_error: 1.9,
    confidence_interval: { low: 4.4, high: 12, confidence_level: 0.95 },
    p_value: 0.004,
    sample_size: 240,
    estimator_version: "did-v2",
    library_name: "statsmodels",
    library_version: "0.14.5",
    technical_diagnostics: {
      design_assessment: "valid",
      causal_claim_allowed: true,
      plain_language_conclusion: "The design supports an estimated causal increase of 8.20.",
      warnings: [],
      sample_counts: { treated_units: 12, control_units: 14 },
      event_study: [{ period: -1, coefficient: 0 }, { period: 1, coefficient: 8.2 }],
      observed_vs_counterfactual: [{ period: 1, observed: 108.2, counterfactual: 100 }],
    },
    business_impact: {
      incremental_outcome: 984,
      relative_lift: 0.082,
      incremental_revenue: 98400,
      incremental_conversions: null,
    },
    created_at: "2026-07-14T20:00:00Z",
  },
};

afterEach(cleanup);

describe("ResultsExperience", () => {
  it("shows a focused loading state", () => {
    render(<ResultsExperience state={{ kind: "loading" }} />);
    expect(screen.getByText("Estimating incremental impact")).toBeInTheDocument();
  });

  it("shows an empty state when no result exists", () => {
    render(<ResultsExperience state={{ kind: "missing" }} />);
    expect(screen.getByText("We couldn’t find this analysis")).toBeInTheDocument();
  });

  it("shows queued and retrying states in customer language", () => {
    render(<ResultsExperience state={{ kind: "ready", data: { ...base, lifecycle_status: "retrying", run_status: "running", result: null } }} />);
    expect(screen.getByText("We’re retrying your analysis")).toBeInTheDocument();
  });

  it("places the main conclusion before technical detail", () => {
    render(<ResultsExperience state={{ kind: "ready", data: base }} />);
    expect(screen.getByRole("heading", { name: /estimated causal increase/i })).toBeInTheDocument();
    expect(screen.getByText("+8.2%")).toBeInTheDocument();
    expect(screen.getByText("Technical details")).toBeInTheDocument();
  });

  it("shows warnings without calling an invalid design causal", () => {
    const invalid = structuredClone(base);
    invalid.result!.technical_diagnostics = {
      ...invalid.result!.technical_diagnostics,
      design_assessment: "invalid",
      causal_claim_allowed: false,
      plain_language_conclusion: "The design does not support a causal claim.",
      warnings: ["Pre-treatment trends differ."],
    };
    render(<ResultsExperience state={{ kind: "ready", data: invalid }} />);
    expect(screen.getByText("Use this result with caution")).toBeInTheDocument();
    expect(screen.getByText("Pre-treatment trends differ.")).toBeInTheDocument();
  });

  it("shows a recoverable failure", () => {
    render(<ResultsExperience state={{ kind: "ready", data: { ...base, lifecycle_status: "failed", run_status: "failed", result: null, failure_information: "Analysis could not be completed." } }} />);
    expect(screen.getByText("This analysis needs attention")).toBeInTheDocument();
  });

  it("shows permission errors without leaking backend text", () => {
    render(<ResultsExperience state={{ kind: "permission" }} />);
    expect(screen.getByText("You don’t have access to this result")).toBeInTheDocument();
  });
});
