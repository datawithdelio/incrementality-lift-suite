import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DataExplorer } from "@/components/data-products/data-explorer";

afterEach(() => {
  cleanup();
});

const backendExplorerResponse = {
  rows: [
    {
      date: "2025-06-30",
      geography: "Newark",
      treatment: 1,
      conversions: 210,
    },
    {
      date: "2025-07-07",
      geography: "Newark",
      treatment: 1,
      conversions: 232,
    },
  ],
  columns: [
    {
      name: "date",
      inferred_type: "date",
      missing_percentage: 0,
      unique_count: 273,
      minimum: "2025-01-01",
      maximum: "2025-09-30",
      mean: null,
      median: null,
    },
    {
      name: "latitude",
      inferred_type: "float",
      missing_percentage: 0,
      unique_count: 16,
      minimum: 37.5407,
      maximum: 43.1566,
      mean: 40.8,
      median: 40.7,
    },
    {
      name: "conversions",
      inferred_type: "integer",
      missing_percentage: 0,
      unique_count: 420,
      minimum: 120,
      maximum: 330,
      mean: 221.4,
      median: 218,
    },
  ],
  total_rows: 4368,
  page: 1,
  page_size: 50,
  total_pages: 88,
  date_range: {
    column: "date",
    minimum: "2025-01-01",
    maximum: "2025-09-30",
  },
  treatment_distribution: {
    treated: 2184,
    control: 2184,
  },
  outcome_distribution: {
    minimum: 120,
    maximum: 330,
    mean: 221.4,
  },
  visualizations: {
    time_column: "date",
    treatment_column: "treatment",
    outcome_column: "conversions",
    treatment_start_date: "2025-07-01",
    trend: [
      {
        period: "2025-06-23",
        treatment_value: 208.4,
        control_value: 205.1,
        treatment_observations: 56,
        control_observations: 56,
        phase: "pre",
      },
      {
        period: "2025-06-30",
        treatment_value: 209.1,
        control_value: 205.8,
        treatment_observations: 56,
        control_observations: 56,
        phase: "pre",
      },
      {
        period: "2025-07-07",
        treatment_value: 228.8,
        control_value: 207.3,
        treatment_observations: 56,
        control_observations: 56,
        phase: "post",
      },
    ],
    distribution: {
      minimum: 120,
      maximum: 330,
      mean: 221.4,
      median: 218,
      first_quartile: 191,
      third_quartile: 246,
      outlier_count: 4,
      sample_size: 4368,
      bins: [],
    },
    missingness: [],
    breakdown_columns: ["geography", "state"],
    breakdowns: {
      geography: [],
      state: [],
    },
    balance: {
      treatment_label: "Treatment",
      treatment_value: "1",
      treatment_count: 2184,
      treatment_percentage: 50,
      control_label: "Control",
      control_value: "0",
      control_count: 2184,
      control_percentage: 50,
      treatment_pre_count: 1448,
      treatment_post_count: 736,
      control_pre_count: 1448,
      control_post_count: 736,
    },
    diagnostics: [],
  },
};

describe("premium Data Explorer experience", () => {
  it("uses backend evidence to present a clean weekly Geo Holdout view", () => {
    render(
      <DataExplorer
        selectedOutcome="conversions"
        state={
          {
            kind: "ready",
            data: backendExplorerResponse,
          } as never
        }
      />,
    );

    expect(
      screen.getByRole("combobox", {
        name: "Outcome",
      }),
    ).toHaveValue("conversions");

    expect(
      screen.getByRole("combobox", {
        name: "Frequency",
      }),
    ).toHaveValue("weekly");

    expect(screen.getByText("Detected intervention date")).toBeInTheDocument();

    expect(screen.getByText("Jul 1, 2025")).toBeInTheDocument();

    expect(screen.getByText("Selected outcome")).toBeInTheDocument();

    const evidenceSummary = screen.getByRole("region", {
      name: "Selected evidence summary",
    });

    expect(
      within(evidenceSummary).getByText("Conversions"),
    ).toBeInTheDocument();

    expect(screen.getByText("Pre-treatment")).toBeInTheDocument();

    expect(screen.getByText("Post-treatment")).toBeInTheDocument();

    expect(screen.queryByText("+9.8%")).not.toBeInTheDocument();

    expect(
      screen.getByRole("region", {
        name: "Treatment and control balance",
      }),
    ).toBeInTheDocument();
  });

  it("removes treatment framing for MMM while preserving raw row columns", () => {
    const mmmResponse = {
      ...backendExplorerResponse,
      rows: [
        {
          ...backendExplorerResponse.rows[0],
          treated: 1,
          post: 0,
          treatment_group: 1,
        },
      ],
    };

    render(
      <DataExplorer
        estimator="marketing_mix_model"
        selectedOutcome="conversions"
        state={
          {
            kind: "ready",
            data: mmmResponse,
          } as never
        }
      />,
    );

    expect(
      screen.queryByRole("region", {
        name: "Treatment and control balance",
      }),
    ).not.toBeInTheDocument();

    const rowTable = screen.getByRole("table");
    expect(
      within(rowTable).getByRole("columnheader", { name: "treated" }),
    ).toBeInTheDocument();
    expect(
      within(rowTable).getByRole("columnheader", { name: "post" }),
    ).toBeInTheDocument();
    expect(
      within(rowTable).getByRole("columnheader", {
        name: "treatment group",
      }),
    ).toBeInTheDocument();
    expect(within(rowTable).queryByText("Treated")).not.toBeInTheDocument();
  });

  it("does not select an unrelated numeric column over the backend outcome", () => {
    render(
      <DataExplorer
        state={
          {
            kind: "ready",
            data: backendExplorerResponse,
          } as never
        }
      />,
    );

    expect(
      screen.getByRole("combobox", {
        name: "Outcome",
      }),
    ).toHaveValue("conversions");

    expect(
      screen.getByRole("combobox", {
        name: "Outcome",
      }),
    ).not.toHaveValue("latitude");
  });
});

describe("unmapped Data Explorer guidance", () => {
  it("does not present the first numeric column as a mapped outcome", () => {
    const unmappedResponse = {
      ...backendExplorerResponse,
      visualizations: {
        ...backendExplorerResponse.visualizations,
        outcome_column: null,
        treatment_start_date: null,
        trend: [],
        balance: {
          ...backendExplorerResponse.visualizations.balance,
          treatment_pre_count: 0,
          treatment_post_count: 0,
          control_pre_count: 0,
          control_post_count: 0,
        },
      },
    };

    render(
      <DataExplorer
        state={
          {
            kind: "ready",
            data: unmappedResponse,
          } as never
        }
      />,
    );

    expect(
      screen.getByRole("combobox", {
        name: "Outcome",
      }),
    ).toHaveValue("");

    expect(
      screen.getByRole("option", {
        name: "Map an outcome first",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Complete semantic mapping to unlock treatment-period insights.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("From the backend dataset mapping"),
    ).not.toBeInTheDocument();
  });
});

describe("premium chart and quality workspace", () => {
  it("shows post-treatment context beside a compact quality summary", () => {
    render(
      <DataExplorer
        selectedOutcome="conversions"
        quality={
          {
            score: 92,
            ready: true,
            findings: [
              {
                rule_id: "outliers",
                passed: false,
                severity: "warning",
                evidence: {
                  outlier_count: 131,
                },
                recommendation: "Review extreme outcomes before analysis.",
              },
              {
                rule_id: "missing_data",
                passed: true,
                severity: "info",
                evidence: {
                  missing_count: 0,
                },
                recommendation: "No action is required.",
              },
            ],
          } as never
        }
        state={
          {
            kind: "ready",
            data: backendExplorerResponse,
          } as never
        }
      />,
    );

    expect(screen.getByText("Post-treatment period")).toBeInTheDocument();

    expect(
      screen.getByRole("complementary", {
        name: "Data quality summary",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("1 issue needs attention")).toBeInTheDocument();
  });
});

describe("interactive chart inspection", () => {
  it("supports hover inspection and click-to-pin", () => {
    render(
      <DataExplorer
        selectedOutcome="conversions"
        state={
          {
            kind: "ready",
            data: backendExplorerResponse,
          } as never
        }
      />,
    );

    const inspectionTarget = screen.getByRole("button", {
      name: /Inspect Jul 7, 2025/i,
    });

    fireEvent.mouseEnter(inspectionTarget);

    const details = screen.getByRole("status", {
      name: "Chart period details",
    });

    expect(within(details).getByText("228.8")).toBeInTheDocument();

    expect(within(details).getByText("207.3")).toBeInTheDocument();

    expect(within(details).getByText("+21.5")).toBeInTheDocument();

    const periodSummary = screen.getByRole("region", {
      name: "Selected chart period",
    });

    expect(within(periodSummary).getByText("Jul 7, 2025")).toBeInTheDocument();

    fireEvent.click(inspectionTarget);

    fireEvent.mouseLeave(
      screen.getByRole("img", {
        name: /Conversions outcome trend/i,
      }),
    );

    expect(
      screen.getByRole("status", {
        name: "Chart period details",
      }),
    ).toBeInTheDocument();

    fireEvent.keyDown(
      screen.getByRole("group", {
        name: "Interactive trend chart",
      }),
      {
        key: "Escape",
      },
    );

    expect(
      screen.queryByRole("status", {
        name: "Chart period details",
      }),
    ).not.toBeInTheDocument();
  });
});

describe("premium row-level evidence table", () => {
  it("formats evidence and lets users choose visible columns", () => {
    const tableResponse = {
      ...backendExplorerResponse,
      rows: [
        {
          ...backendExplorerResponse.rows[0],
          treatment_group: "treated",
          revenue: 25459.64,
          conversion_rate: 0.033985,
        },
      ],
      columns: [
        ...backendExplorerResponse.columns,
        {
          name: "treatment_group",
          inferred_type: "string",
          missing_percentage: 0,
          unique_count: 2,
          minimum: null,
          maximum: null,
          mean: null,
          median: null,
        },
        {
          name: "revenue",
          inferred_type: "float",
          missing_percentage: 0,
          unique_count: 4200,
          minimum: 1000,
          maximum: 50000,
          mean: 25000,
          median: 24500,
        },
        {
          name: "conversion_rate",
          inferred_type: "float",
          missing_percentage: 0,
          unique_count: 4200,
          minimum: 0,
          maximum: 1,
          mean: 0.03,
          median: 0.03,
        },
      ],
    };

    render(
      <DataExplorer
        exportHref="/preview.csv?column_search="
        onPreviousPage={() => undefined}
        onNextPage={() => undefined}
        state={
          {
            kind: "ready",
            data: tableResponse,
          } as never
        }
      />,
    );

    const table = screen.getByRole("table");

    expect(
      screen.getByRole("link", {
        name: "Download CSV",
      }),
    ).toHaveAttribute("href", "/preview.csv?column_search=");

    expect(
      screen.getByRole("button", {
        name: "Previous",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("button", {
        name: "Next",
      }),
    ).toBeEnabled();

    expect(within(table).getByText("$25,459.64")).toBeInTheDocument();

    expect(within(table).getByText("3.4%")).toBeInTheDocument();

    expect(within(table).getByText("Treated")).toHaveClass(
      "explorer-treatment-pill",
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: /Columns/i,
      }),
    );

    const columnChooser = screen.getByRole("group", {
      name: "Visible table columns",
    });

    fireEvent.click(
      within(columnChooser).getByRole("checkbox", {
        name: "Revenue column",
      }),
    );

    expect(
      within(table).queryByRole("columnheader", {
        name: "revenue",
      }),
    ).not.toBeInTheDocument();
  });
});
