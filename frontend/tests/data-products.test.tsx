import {
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

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

  it("explains mapped evidence through linked visualization tabs", () => {
    const filterMissing = vi.fn();

    render(
      <DataExplorer
        onFilterMissing={filterMissing}
        state={{
          kind: "ready",
          data: {
            rows: [
              {
                date: "2026-01-01",
                market: "Boston",
                region: null,
                treated: false,
                revenue: 100,
              },
            ],
            columns: [
              {
                name: "revenue",
                inferred_type: "integer",
                missing_percentage: 0,
                unique_count: 5,
                minimum: 100,
                maximum: 150,
                mean: 122,
                median: 110,
              },
            ],
            total_rows: 5,
            page: 1,
            page_size: 50,
            total_pages: 1,
            date_range: {
              column: "date",
              minimum: "2026-01-01",
              maximum: "2026-02-01",
            },
            treatment_distribution: {
              yes: 3,
              no: 2,
            },
            outcome_distribution: {
              minimum: 100,
              maximum: 150,
              mean: 122,
            },
            visualizations: {
              time_column: "date",
              treatment_column: "treated",
              outcome_column: "revenue",
              treatment_start_date: "2026-02-01",
              trend: [
                {
                  period: "2026-01-01",
                  treatment_value: 110,
                  control_value: 100,
                  treatment_observations: 1,
                  control_observations: 1,
                  phase: "pre",
                },
                {
                  period: "2026-02-01",
                  treatment_value: 147.5,
                  control_value: 105,
                  treatment_observations: 2,
                  control_observations: 1,
                  phase: "post",
                },
              ],
              distribution: {
                minimum: 100,
                maximum: 150,
                mean: 122,
                median: 110,
                first_quartile: 105,
                third_quartile: 145,
                outlier_count: 0,
                sample_size: 5,
                bins: [
                  {
                    minimum: 100,
                    maximum: 125,
                    treatment_count: 1,
                    control_count: 2,
                  },
                  {
                    minimum: 125,
                    maximum: 150,
                    treatment_count: 2,
                    control_count: 0,
                  },
                ],
              },
              missingness: [
                {
                  column: "region",
                  missing_count: 2,
                  missing_percentage: 40,
                },
                {
                  column: "revenue",
                  missing_count: 0,
                  missing_percentage: 0,
                },
              ],
              balance: {
                treatment_label: "Treatment",
                treatment_value: "yes",
                treatment_count: 3,
                treatment_percentage: 60,
                control_label: "Control",
                control_value: "no",
                control_count: 2,
                control_percentage: 40,
                treatment_pre_count: 1,
                treatment_post_count: 2,
                control_pre_count: 1,
                control_post_count: 1,
                status: "Needs review",
              },
              breakdowns: {
                market: [
                  {
                    value: "Boston",
                    outcome_mean: 102.5,
                    observation_count: 2,
                    treatment_count: 0,
                    control_count: 2,
                  },
                  {
                    value: "New York",
                    outcome_mean: 127.5,
                    observation_count: 2,
                    treatment_count: 2,
                    control_count: 0,
                  },
                ],
              },
            },
          },
        }}
        quality={{
          score: 82,
          ready: true,
          findings: [
            {
              rule_id: "date_gaps",
              severity: "warning",
              passed: false,
              evidence: {
                gap_count: 2,
              },
              recommendation: "Fill missing periods.",
            },
          ],
        }}
      />,
    );

    expect(
      screen.getByRole("tab", {
        name: "Trend",
      }),
    ).toHaveAttribute("aria-selected", "true");

    expect(
      screen.getByRole("img", {
        name: "Revenue outcome trend",
      }),
    ).toBeInTheDocument();

    expect(screen.getAllByText("Treatment")).not.toHaveLength(0);
    expect(screen.getAllByText("Control")).not.toHaveLength(0);
    expect(
      screen.getByText("Treatment begins Feb 1, 2026"),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("tab", {
        name: "Distribution",
      }),
    );

    expect(screen.getByText("Median")).toBeInTheDocument();
    expect(screen.getByText("First quartile")).toBeInTheDocument();
    expect(screen.getByText("5 observations")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("tab", {
        name: "Missingness",
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Filter to 2 rows missing region",
      }),
    );

    expect(filterMissing).toHaveBeenCalledWith("region");

    fireEvent.click(
      screen.getByRole("tab", {
        name: "Breakdown",
      }),
    );

    expect(
      screen.getByRole("combobox", {
        name: "Break down outcome by",
      }),
    ).toHaveValue("market");

    expect(
      screen.getByRole("button", {
        name: "Download chart as PNG",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("2 gaps detected")).toBeInTheDocument();
  });
});

describe("ReportHistory", () => {
  it("shows generation, retry, failure, and downloadable versions", () => {
    render(<ReportHistory reports={[{ id: "1", version: 3, format: "pdf", status: "succeeded", attempt_count: 1, max_attempts: 3, failure_reason: null, created_at: "2026-07-14" }, { id: "2", version: 2, format: "csv", status: "pending", attempt_count: 1, max_attempts: 3, failure_reason: "Report generation failed safely.", created_at: "2026-07-13" }, { id: "3", version: 1, format: "pdf", status: "failed", attempt_count: 3, max_attempts: 3, failure_reason: "Report generation failed safely.", created_at: "2026-07-12" }]} workspaceId="workspace-1" projectId="project-1" runId="run-1" />);
    expect(screen.getByText("PDF · version 3")).toBeInTheDocument();
    expect(screen.getByText("Retrying")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download" })).toBeInTheDocument();
  });
});

describe("DataExplorer value rendering", () => {
  it("renders semantic table cells for null, numeric, and boolean backend values", () => {
    render(
      <DataExplorer
        state={{
          kind: "ready",
          data: {
            rows: [
              {
                market: "Boston",
                revenue: 120.5,
                treated: true,
                notes: null,
              },
            ],
            columns: [
              {
                name: "market",
                inferred_type: "string",
                missing_percentage: 0,
                unique_count: 1,
                minimum: null,
                maximum: null,
                mean: null,
                median: null,
              },
              {
                name: "revenue",
                inferred_type: "float",
                missing_percentage: 0,
                unique_count: 1,
                minimum: 120.5,
                maximum: 120.5,
                mean: 120.5,
                median: 120.5,
              },
              {
                name: "treated",
                inferred_type: "boolean",
                missing_percentage: 0,
                unique_count: 1,
                minimum: null,
                maximum: null,
                mean: null,
                median: null,
              },
              {
                name: "notes",
                inferred_type: "string",
                missing_percentage: 100,
                unique_count: 0,
                minimum: null,
                maximum: null,
                mean: null,
                median: null,
              },
            ],
            total_rows: 1,
            page: 1,
            page_size: 50,
            total_pages: 1,
            date_range: null,
            treatment_distribution: {},
            outcome_distribution: {},
          },
        }}
      />,
    );

    expect(
      screen.getByRole("table"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("columnheader", { name: "market" }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("columnheader", { name: "revenue" }),
    ).toBeInTheDocument();

    expect(screen.getByText("120.5")).toBeInTheDocument();
    expect(screen.getByText("true")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

describe("DataExplorer dataset metadata", () => {
  it("shows useful dataset metadata without exposing private storage details", () => {
    render(
      <DataExplorer
        dataset={{
          id: "dataset-1",
          workspace_id: "workspace-1",
          project_id: "project-1",
          created_by_user_id: "user-1",
          source_filename: "campaign-results.csv",
          storage_key: "private/storage/path.csv",
          media_type: "text/csv",
          byte_size: 2048,
          checksum_sha256: "a".repeat(64),
          status: "ready",
          created_at: "2026-07-18T12:00:00Z",
          uploaded_at: "2026-07-18T12:05:00Z",
          validation_started_at: "2026-07-18T12:06:00Z",
          validation_completed_at: "2026-07-18T12:07:00Z",
          row_count: 1537,
          column_count: 13,
          failure_reason: null,
        }}
        state={{
          kind: "ready",
          data: {
            rows: [{ market: "Boston" }],
            columns: [],
            total_rows: 1537,
            page: 1,
            page_size: 50,
            total_pages: 31,
            date_range: null,
            treatment_distribution: {},
            outcome_distribution: {},
          },
        }}
      />,
    );

    expect(
      screen.getByText("campaign-results.csv"),
    ).toBeInTheDocument();

    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("1,537")).toBeInTheDocument();
    expect(screen.getByText("13")).toBeInTheDocument();
    expect(screen.getByText("2 KB")).toBeInTheDocument();
    expect(screen.getByText("Uploaded")).toBeInTheDocument();
    expect(
      screen.getByText(
        new Date(
          "2026-07-18T12:05:00Z",
        ).toLocaleString(),
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("private/storage/path.csv"),
    ).not.toBeInTheDocument();

    expect(
      screen.queryByText("a".repeat(64)),
    ).not.toBeInTheDocument();
  });
});
