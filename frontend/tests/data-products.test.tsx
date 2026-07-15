import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DataExplorer } from "../src/components/data-products/data-explorer";
import { ReportHistory } from "../src/components/data-products/report-history";

afterEach(cleanup);

describe("DataExplorer", () => {
  it("renders loading, permission, and empty states", () => {
    const { rerender } = render(<DataExplorer state={{ kind: "loading" }} />);
    expect(screen.getByText("Profiling your dataset")).toBeInTheDocument();
    rerender(<DataExplorer state={{ kind: "permission" }} />);
    expect(screen.getByText("You don’t have access to this dataset")).toBeInTheDocument();
    rerender(<DataExplorer state={{ kind: "ready", data: { rows: [], columns: [], total_rows: 0, page: 1, page_size: 50, total_pages: 0, date_range: null, treatment_distribution: {}, outcome_distribution: {} } }} />);
    expect(screen.getByText("This dataset has no rows")).toBeInTheDocument();
  });

  it("shows paginated values, profiles, distributions, and quality findings", () => {
    render(<DataExplorer state={{ kind: "ready", data: { rows: [{ market: "Boston", treated: "yes", revenue: "120" }], columns: [{ name: "revenue", inferred_type: "integer", missing_percentage: 0, unique_count: 40, minimum: 80, maximum: 140, mean: 110, median: 109 }], total_rows: 250000, page: 2, page_size: 50, total_pages: 5000, date_range: { column: "date", minimum: "2026-01-01", maximum: "2026-07-01" }, treatment_distribution: { yes: 20, no: 20 }, outcome_distribution: { minimum: 80, maximum: 140, mean: 110 } } }} quality={{ score: 82, ready: true, findings: [{ rule_id: "date_gaps", severity: "warning", passed: true, evidence: { gap_count: 2 }, recommendation: "Fill missing periods." }] }} />);
    expect(screen.getByText("250,000 rows")).toBeInTheDocument();
    expect(screen.getByText("Page 2 of 5,000")).toBeInTheDocument();
    expect(screen.getAllByText("82/100")).toHaveLength(2);
    expect(screen.getByText("Fill missing periods.")).toBeInTheDocument();
  });
});

describe("ReportHistory", () => {
  it("shows generation, retry, failure, and downloadable versions", () => {
    render(<ReportHistory reports={[{ id: "1", version: 3, format: "pdf", status: "succeeded", attempt_count: 1, max_attempts: 3, failure_reason: null, created_at: "2026-07-14" }, { id: "2", version: 2, format: "csv", status: "pending", attempt_count: 1, max_attempts: 3, failure_reason: "Report generation failed safely.", created_at: "2026-07-13" }, { id: "3", version: 1, format: "pdf", status: "failed", attempt_count: 3, max_attempts: 3, failure_reason: "Report generation failed safely.", created_at: "2026-07-12" }]} downloadBase="/api" />);
    expect(screen.getByText("PDF · version 3")).toBeInTheDocument();
    expect(screen.getByText("Retrying")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download" })).toBeInTheDocument();
  });
});
