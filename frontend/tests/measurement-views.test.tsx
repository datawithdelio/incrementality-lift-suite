import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ChannelPerformance } from "../src/components/measurement/channel-performance";
import { ResultsDashboard } from "../src/components/measurement/results-dashboard";
import type { DashboardResponse } from "../src/lib/measurement/types";

afterEach(cleanup);

const dashboard: DashboardResponse = {
  total_runs: 3, succeeded_runs: 1, failed_runs: 1, active_runs: 1,
  runs: [
    { run_id: "r1", project_id: "p1", project_name: "Acquisition", status: "succeeded", estimator_type: "difference_in_differences", method_label: "Difference In Differences", metric_label: "Treatment effect", effect: 4.2, confidence_low: 2, confidence_high: 6.4, reliability: "valid", business_impact: 1200, warnings: [], created_at: "2026-07-01T00:00:00Z", failure_reason: null },
    { run_id: "r2", project_id: "p2", project_name: "Brand", status: "failed", estimator_type: "synthetic_control", method_label: "Synthetic Control", metric_label: "Synthetic-control gap", effect: null, confidence_low: null, confidence_high: null, reliability: "unknown", business_impact: null, warnings: ["Poor pre-period fit"], created_at: "2026-06-30T00:00:00Z", failure_reason: "Insufficient donors" },
    { run_id: "r3", project_id: "p1", project_name: "Acquisition", status: "running", estimator_type: "off_policy_evaluation", method_label: "Off Policy Evaluation", metric_label: "Estimated policy value", effect: null, confidence_low: null, confidence_high: null, reliability: "unknown", business_impact: null, warnings: [], created_at: "2026-06-29T00:00:00Z", failure_reason: null },
  ],
};

describe("ResultsDashboard", () => {
  it("shows loading and empty states", () => {
    const { rerender } = render(<ResultsDashboard state={{ kind: "loading" }} workspaceId="w1" />);
    expect(screen.getByText("Loading your measurement program")).toBeInTheDocument();
    rerender(<ResultsDashboard state={{ kind: "ready", data: { ...dashboard, total_runs: 0, runs: [] } }} workspaceId="w1" />);
    expect(screen.getByText("No analysis runs match these filters")).toBeInTheDocument();
  });

  it("shows partial, failed, and mixed-method states with explicit labels", () => {
    render(<ResultsDashboard state={{ kind: "ready", data: dashboard }} workspaceId="w1" />);
    expect(screen.getByText("Treatment effect")).toBeInTheDocument();
    expect(screen.getByText("Synthetic-control gap")).toBeInTheDocument();
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText("Insufficient donors")).toBeInTheDocument();
  });
});

describe("ChannelPerformance", () => {
  it("distinguishes observed and incremental ROAS and shows recommendations", () => {
    render(<ChannelPerformance state={{ kind: "ready", data: { channels: [{ channel: "Paid Search", spend: 500, incremental_revenue: 1200, incremental_conversions: 80, lift: 0.12, incremental_roas: 2.4, observed_roas: 3, confidence_low: 1, confidence_high: 3.8, contribution: 0.4, marginal_response: 1.2, reliability: "strong", recommended_movement: "increase", warning: "Strong incremental evidence supports a measured increase." }] } }} />);
    expect(screen.getByText("Incremental ROAS")).toBeInTheDocument();
    expect(screen.getByText("Observed ROAS")).toBeInTheDocument();
    expect(screen.getByText("Increase")).toBeInTheDocument();
  });
});
