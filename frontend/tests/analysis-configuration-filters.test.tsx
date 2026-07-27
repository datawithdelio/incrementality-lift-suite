import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SESSION_TOKEN_KEY } from "../src/lib/auth/api";

const {
  fetchGeographySummaryMock,
  fetchPreviewMock,
  getProjectOverviewMock,
  getDatasetMock,
  getLatestSemanticMappingMock,
} = vi.hoisted(() => ({
  fetchGeographySummaryMock: vi.fn(),
  fetchPreviewMock: vi.fn(),
  getProjectOverviewMock: vi.fn(),
  getDatasetMock: vi.fn(),
  getLatestSemanticMappingMock: vi.fn(),
}));

vi.mock("../src/lib/data-products/api", async () => {
  const actual = await vi.importActual<
    typeof import("../src/lib/data-products/api")
  >("../src/lib/data-products/api");

  return {
    ...actual,
    fetchGeographySummary: fetchGeographySummaryMock,
    fetchPreview: fetchPreviewMock,
  };
});

vi.mock("../src/lib/projects/api", async () => {
  const actual = await vi.importActual<
    typeof import("../src/lib/projects/api")
  >("../src/lib/projects/api");

  return {
    ...actual,
    getProjectOverview: getProjectOverviewMock,
  };
});

vi.mock("../src/lib/datasets/api", async () => {
  const actual = await vi.importActual<
    typeof import("../src/lib/datasets/api")
  >("../src/lib/datasets/api");

  return {
    ...actual,
    getDataset: getDatasetMock,
  };
});

vi.mock("../src/lib/semantic-mapping/api", async () => {
  const actual = await vi.importActual<
    typeof import("../src/lib/semantic-mapping/api")
  >("../src/lib/semantic-mapping/api");

  return {
    ...actual,
    getLatestSemanticMapping: getLatestSemanticMappingMock,
  };
});

import { AnalysisConfigurationClient } from "../src/components/analysis-configuration/analysis-configuration-client";

describe("Analysis Configuration filters and selections", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    window.localStorage.setItem(SESSION_TOKEN_KEY, "session-token");

    getProjectOverviewMock.mockResolvedValue({
      id: "project-1",
      workspace_id: "workspace-1",
      created_by_user_id: "user-1",
      name: "Lift Study",
      slug: "lift-study",
      description: null,
      status: "active",
      created_at: "2026-07-18T00:00:00Z",
      archived_at: null,
      latest_dataset_id: "dataset-1",
      latest_dataset_status: "ready",
      semantic_mapping_configured: true,
      latest_analysis_run_id: null,
      latest_analysis_run_status: null,
    });

    getDatasetMock.mockResolvedValue({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "lift.csv",
      storage_key: "datasets/lift.csv",
      media_type: "text/csv",
      byte_size: 1000,
      checksum_sha256: "abc123",
      status: "ready",
      created_at: "2026-07-18T00:00:00Z",
      uploaded_at: "2026-07-18T00:01:00Z",
      validation_started_at: "2026-07-18T00:02:00Z",
      validation_completed_at: "2026-07-18T00:03:00Z",
      row_count: 100,
      column_count: 6,
      failure_reason: null,
    });

    getLatestSemanticMappingMock.mockResolvedValue({
      id: "mapping-1",
      dataset_id: "dataset-1",
      created_by_user_id: "user-1",
      version: 3,
      time_column: "date",
      unit_column: "geo",
      treatment_column: "treated",
      outcome_column: "revenue",
      spend_column: "spend",
      covariate_columns: ["segment"],
      treatment_value: "1",
      control_value: "0",
      created_at: "2026-07-18T00:04:00Z",
      updated_at: "2026-07-18T00:04:00Z",
    });

    fetchGeographySummaryMock.mockResolvedValue({
      mapping_version: 3,
      unit_column: "geo",
      total_geographies: 3,
      geographies: [
        {
          value: "Boston",
          observation_count: 40,
          latitude: 42.3601,
          longitude: -71.0589,
          coordinate_status: "verified",
          metrics: {
            outcome_sum: 4000,
            spend_sum: 800,
            covariate_sums: {
              segment: 0,
            },
          },
        },
        {
          value: "Chicago",
          observation_count: 35,
          latitude: 41.8781,
          longitude: -87.6298,
          coordinate_status: "verified",
          metrics: {
            outcome_sum: 3150,
            spend_sum: 630,
            covariate_sums: {
              segment: 0,
            },
          },
        },
        {
          value: "Newark",
          observation_count: 25,
          latitude: null,
          longitude: null,
          coordinate_status: "missing",
          metrics: {
            outcome_sum: 2250,
            spend_sum: 450,
            covariate_sums: {
              segment: 0,
            },
          },
        },
      ],
    });

    fetchPreviewMock.mockResolvedValue({
      rows: [
        {
          date: "2025-01-01",
          geo: "Boston",
          treated: 1,
          revenue: 100,
          spend: 20,
          segment: "Enterprise",
        },
        {
          date: "2025-01-02",
          geo: "Chicago",
          treated: 0,
          revenue: 90,
          spend: 18,
          segment: "SMB",
        },
      ],
      columns: [
        {
          name: "date",
          inferred_type: "date",
          missing_percentage: 0,
          unique_count: 2,
          minimum: "2025-01-01",
          maximum: "2025-01-02",
          mean: null,
          median: null,
        },
        {
          name: "geo",
          inferred_type: "string",
          missing_percentage: 0,
          unique_count: 2,
          minimum: null,
          maximum: null,
          mean: null,
          median: null,
        },
        {
          name: "treated",
          inferred_type: "integer",
          missing_percentage: 0,
          unique_count: 2,
          minimum: 0,
          maximum: 1,
          mean: 0.5,
          median: 0.5,
        },
        {
          name: "revenue",
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
        {
          name: "segment",
          inferred_type: "string",
          missing_percentage: 0,
          unique_count: 2,
          minimum: null,
          maximum: null,
          mean: null,
          median: null,
        },
      ],
      total_rows: 2,
      page: 1,
      page_size: 50,
      total_pages: 1,
      date_range: {
        column: "date",
        minimum: "2025-01-01",
        maximum: "2025-01-02",
      },
      treatment_distribution: {
        "0": 1,
        "1": 1,
      },
      outcome_distribution: {},
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("moves from a valid period to filters using real scoped dataset columns", async () => {
    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: /Difference in Differences/i,
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.change(screen.getByLabelText("Analysis start date"), {
      target: {
        value: "2025-01-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Intervention date"), {
      target: {
        value: "2025-02-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Analysis end date"), {
      target: {
        value: "2025-03-31",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Filter and select population",
      }),
    ).toBeInTheDocument();

    const filterColumn = screen.getByLabelText("Filter column");

    expect(filterColumn).toContainHTML('<option value="geo">geo</option>');

    expect(filterColumn).toContainHTML(
      '<option value="revenue">revenue</option>',
    );

    expect(filterColumn).toContainHTML(
      '<option value="segment">segment</option>',
    );

    expect(fetchPreviewMock).toHaveBeenCalledWith(
      "workspace-1",
      "project-1",
      "dataset-1",
      {
        page: 1,
        search: "",
        sortColumn: "",
        descending: false,
        filterColumn: "",
        filterValue: "",
      },
      "session-token",
      expect.any(AbortSignal),
    );
  }, 15_000);
  it("uses column types to offer valid filter operators and typed values", async () => {
    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: /Difference in Differences/i,
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.change(screen.getByLabelText("Analysis start date"), {
      target: {
        value: "2025-01-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Intervention date"), {
      target: {
        value: "2025-02-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Analysis end date"), {
      target: {
        value: "2025-03-31",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    await screen.findByRole("heading", {
      name: "Filter and select population",
    });

    fireEvent.change(screen.getByLabelText("Filter column"), {
      target: {
        value: "revenue",
      },
    });

    const numericOperator = screen.getByLabelText("Filter operator");

    expect(numericOperator).toContainHTML(
      '<option value="greater_than">Greater than</option>',
    );

    expect(numericOperator).not.toContainHTML(
      '<option value="contains">Contains</option>',
    );

    expect(screen.getByLabelText("Filter value")).toHaveAttribute(
      "type",
      "number",
    );

    fireEvent.change(screen.getByLabelText("Filter column"), {
      target: {
        value: "geo",
      },
    });

    expect(screen.getByLabelText("Filter operator")).toContainHTML(
      '<option value="contains">Contains</option>',
    );

    expect(screen.getByLabelText("Filter value")).toHaveAttribute(
      "type",
      "text",
    );
  });

  it("adds and removes a typed filter rule from the analysis draft", async () => {
    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: /Difference in Differences/i,
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.change(screen.getByLabelText("Analysis start date"), {
      target: {
        value: "2025-01-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Intervention date"), {
      target: {
        value: "2025-02-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Analysis end date"), {
      target: {
        value: "2025-03-31",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    await screen.findByRole("heading", {
      name: "Filter and select population",
    });

    fireEvent.change(screen.getByLabelText("Filter column"), {
      target: {
        value: "revenue",
      },
    });

    fireEvent.change(screen.getByLabelText("Filter operator"), {
      target: {
        value: "greater_than",
      },
    });

    fireEvent.change(screen.getByLabelText("Filter value"), {
      target: {
        value: "95",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Add filter",
      }),
    );

    expect(screen.getByText("revenue · Greater than · 95")).toBeInTheDocument();

    expect(screen.getByLabelText("Filter column")).toHaveValue("");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Remove filter revenue",
      }),
    );

    expect(
      screen.queryByText("revenue · Greater than · 95"),
    ).not.toBeInTheDocument();
  });

  it("allows null filters without entering a value", async () => {
    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: /Difference in Differences/i,
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.change(screen.getByLabelText("Analysis start date"), {
      target: {
        value: "2025-01-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Intervention date"), {
      target: {
        value: "2025-02-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Analysis end date"), {
      target: {
        value: "2025-03-31",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    await screen.findByRole("heading", {
      name: "Filter and select population",
    });

    fireEvent.change(screen.getByLabelText("Filter column"), {
      target: {
        value: "geo",
      },
    });

    fireEvent.change(screen.getByLabelText("Filter operator"), {
      target: {
        value: "is_null",
      },
    });

    expect(screen.queryByLabelText("Filter value")).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Add filter",
      }),
    );

    expect(screen.getByText("geo · Is null")).toBeInTheDocument();
  });

  it("selects geographies and segments from observed dataset values without overlap", async () => {
    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: /Difference in Differences/i,
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.change(screen.getByLabelText("Analysis start date"), {
      target: {
        value: "2025-01-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Intervention date"), {
      target: {
        value: "2025-02-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Analysis end date"), {
      target: {
        value: "2025-03-31",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    await screen.findByRole("heading", {
      name: "Filter and select population",
    });

    const includeBoston = screen.getByRole("checkbox", {
      name: "Include geography Boston",
    });

    const excludeBoston = screen.getByRole("checkbox", {
      name: "Exclude geography Boston",
    });

    fireEvent.click(includeBoston);

    expect(includeBoston).toBeChecked();

    expect(excludeBoston).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Segment column"), {
      target: {
        value: "segment",
      },
    });

    const includeEnterprise = screen.getByRole("checkbox", {
      name: "Include segment Enterprise",
    });

    const excludeEnterprise = screen.getByRole("checkbox", {
      name: "Exclude segment Enterprise",
    });

    fireEvent.click(includeEnterprise);

    expect(includeEnterprise).toBeChecked();

    expect(excludeEnterprise).toBeDisabled();

    expect(
      screen.getByRole("checkbox", {
        name: "Include geography Chicago",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("checkbox", {
        name: "Include geography Newark",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("3")).toBeInTheDocument();

    expect(
      screen.getByRole("checkbox", {
        name: "Include segment SMB",
      }),
    ).toBeInTheDocument();
  });

  it("presents geography selection as accessible cards with visible state", async () => {
    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: /Difference in Differences/i,
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.change(screen.getByLabelText("Analysis start date"), {
      target: {
        value: "2025-01-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Intervention date"), {
      target: {
        value: "2025-02-01",
      },
    });

    fireEvent.change(screen.getByLabelText("Analysis end date"), {
      target: {
        value: "2025-03-31",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    const geographyRegion = await screen.findByRole("region", {
      name: "Geography selection cards",
    });

    const bostonCard = screen.getByRole("article", {
      name: "Geography Boston",
    });

    expect(geographyRegion).toHaveClass("analysis-geography-grid");
    expect(bostonCard).toHaveClass("analysis-geography-card");
    expect(bostonCard).toHaveAttribute("data-state", "neutral");

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Include geography Boston",
      }),
    );

    expect(bostonCard).toHaveAttribute("data-state", "included");

    expect(
      screen.getByRole("checkbox", {
        name: "Exclude geography Boston",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("button", {
        name: "Continue",
      }),
    ).toHaveClass("analysis-population-continue");
  }, 15_000);
});
