import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DataQualityView } from "../src/components/data-products/data-quality-view";

afterEach(cleanup);

describe("DataQualityView", () => {
  it("shows backend-defined blocking findings and prevents readiness messaging", () => {
    render(
      <DataQualityView
        quality={{
          score: 48,
          ready: false,
          findings: [
            {
              rule_id: "missing_outcome",
              severity: "blocking",
              passed: false,
              evidence: {
                column: "revenue",
                missing_count: 25,
              },
              recommendation: "Correct the outcome values and upload a new dataset.",
            },
          ],
        }}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Data Quality" }),
    ).toBeInTheDocument();

    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    expect(screen.getByText("Blocking")).toBeInTheDocument();
    expect(screen.getByText("missing_outcome")).toBeInTheDocument();

    expect(
      screen.getByText(
        "Correct the outcome values and upload a new dataset.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "This dataset cannot be used for analysis until the blocking issues are corrected.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("Dataset ready"),
    ).not.toBeInTheDocument();
  });
});

describe("DataQualityView warning readiness", () => {
  it("shows non-blocking warnings while preserving backend readiness", () => {
    render(
      <DataQualityView
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
              recommendation: "Review missing periods before analysis.",
            },
          ],
        }}
      />,
    );

    expect(
      screen.getByText("Dataset ready with warnings"),
    ).toBeInTheDocument();

    expect(screen.getByText("Warning")).toBeInTheDocument();

    expect(
      screen.getByText(
        "You may continue, but review these issues before running an analysis.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Review missing periods before analysis."),
    ).toBeInTheDocument();

    expect(
      screen.queryByText(
        "This dataset cannot be used for analysis until the blocking issues are corrected.",
      ),
    ).not.toBeInTheDocument();
  });
});

describe("DataQualityView validation summary", () => {
  it("summarizes issue severities and separates passed checks", () => {
    render(
      <DataQualityView
        quality={{
          score: 76,
          ready: false,
          findings: [
            {
              rule_id: "missing_outcome",
              severity: "blocking",
              passed: false,
              evidence: {},
              recommendation: "Correct missing outcome values.",
            },
            {
              rule_id: "date_gaps",
              severity: "warning",
              passed: false,
              evidence: {},
              recommendation: "Review missing periods.",
            },
            {
              rule_id: "small_sample",
              severity: "info",
              passed: false,
              evidence: {},
              recommendation: "Review sample size.",
            },
            {
              rule_id: "file_format",
              severity: "info",
              passed: true,
              evidence: {},
              recommendation: "",
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("1 blocking issue")).toBeInTheDocument();
    expect(screen.getByText("1 warning")).toBeInTheDocument();
    expect(screen.getByText("1 info")).toBeInTheDocument();
    expect(screen.getByText("1 passed check")).toBeInTheDocument();

    expect(
      screen.getByRole("heading", { name: "Passed checks" }),
    ).toBeInTheDocument();

    expect(screen.getByText("file_format")).toBeInTheDocument();
  });
});

describe("DataQualityView no-issues state", () => {
  it("shows a clear empty state when validation returns no findings", () => {
    render(
      <DataQualityView
        quality={{
          score: 100,
          ready: true,
          findings: [],
        }}
      />,
    );

    expect(screen.getByText("Dataset ready")).toBeInTheDocument();

    expect(
      screen.getByText("No data-quality issues were found."),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("heading", { name: "Passed checks" }),
    ).not.toBeInTheDocument();
  });
});

describe("DataQualityView load states", () => {
  it("renders explicit loading and safe error states", () => {
    const { rerender } = render(
      <DataQualityView state={{ kind: "loading" }} />,
    );

    expect(
      screen.getByText("Loading validation summary"),
    ).toBeInTheDocument();

    rerender(
      <DataQualityView state={{ kind: "error" }} />,
    );

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(
      "We couldn't load the data-quality results.",
    );
  });
});
