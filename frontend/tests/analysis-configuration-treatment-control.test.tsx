import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SESSION_TOKEN_KEY } from "../src/lib/auth/api";

const {
  fetchPreviewMock,
  fetchGeographySummaryMock,
  getProjectOverviewMock,
  getDatasetMock,
  getLatestSemanticMappingMock,
  queueAnalysisRunMock,
  pushMock,
} = vi.hoisted(() => ({
  fetchPreviewMock: vi.fn(),
  fetchGeographySummaryMock: vi.fn(),
  getProjectOverviewMock: vi.fn(),
  getDatasetMock: vi.fn(),
  getLatestSemanticMappingMock: vi.fn(),
  queueAnalysisRunMock: vi.fn(),
  pushMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("../src/lib/data-products/api", async () => {
  const actual = await vi.importActual<
    typeof import("../src/lib/data-products/api")
  >("../src/lib/data-products/api");

  return {
    ...actual,
    fetchPreview: fetchPreviewMock,
    fetchGeographySummary: fetchGeographySummaryMock,
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

vi.mock("../src/lib/analysis-configuration/api", async () => {
  const actual = await vi.importActual<
    typeof import("../src/lib/analysis-configuration/api")
  >("../src/lib/analysis-configuration/api");

  return {
    ...actual,
    queueAnalysisRun: queueAnalysisRunMock,
  };
});

import { AnalysisRunApiError } from "../src/lib/analysis-configuration/api";

import { AnalysisConfigurationClient } from "../src/components/analysis-configuration/analysis-configuration-client";

describe("Analysis Configuration treatment and control", () => {
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
      dataset_id: "dataset-1",
      mapping_version: 3,
      unit_column: "geo",
      total_geographies: 3,
      geographies: [
        {
          value: "Austin",
          observation_count: 1,
          latitude: 30.2672,
          longitude: -97.7431,
          coordinate_status: "verified",
          metrics: {
            outcome_sum: 95,
            spend_sum: 19,
            covariate_sums: {},
          },
        },
        {
          value: "Boston",
          observation_count: 1,
          latitude: 42.3601,
          longitude: -71.0589,
          coordinate_status: "verified",
          metrics: {
            outcome_sum: 100,
            spend_sum: 20,
            covariate_sums: {},
          },
        },
        {
          value: "Chicago",
          observation_count: 1,
          latitude: 41.8781,
          longitude: -87.6298,
          coordinate_status: "verified",
          metrics: {
            outcome_sum: 90,
            spend_sum: 18,
            covariate_sums: {},
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
        {
          date: "2025-01-03",
          geo: "Austin",
          treated: 0,
          revenue: 95,
          spend: 19,
          segment: "Enterprise",
        },
      ],
      columns: [
        {
          name: "date",
          inferred_type: "date",
          missing_percentage: 0,
          unique_count: 3,
          minimum: "2025-01-01",
          maximum: "2025-01-03",
          mean: null,
          median: null,
        },
        {
          name: "geo",
          inferred_type: "string",
          missing_percentage: 0,
          unique_count: 3,
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
          mean: 0.33,
          median: 0,
        },
        {
          name: "revenue",
          inferred_type: "float",
          missing_percentage: 0,
          unique_count: 3,
          minimum: 90,
          maximum: 100,
          mean: 95,
          median: 95,
        },
        {
          name: "spend",
          inferred_type: "float",
          missing_percentage: 0,
          unique_count: 3,
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
      total_rows: 3,
      page: 1,
      page_size: 50,
      total_pages: 1,
      date_range: {
        column: "date",
        minimum: "2025-01-01",
        maximum: "2025-01-03",
      },
      treatment_distribution: {
        "0": 2,
        "1": 1,
      },
      outcome_distribution: {},
    });
  });

  afterEach(() => {
    cleanup();
  });

  async function moveToFilters(estimatorName: RegExp): Promise<void> {
    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: estimatorName,
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

    if (screen.queryByLabelText("Intervention date")) {
      fireEvent.change(screen.getByLabelText("Intervention date"), {
        target: {
          value: "2025-02-01",
        },
      });
    }

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
  }

  it("shows the mapped DiD treatment definition as read-only", async () => {
    await moveToFilters(/Difference in Differences/i);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Treatment and control setup",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("Treatment column: treated")).toBeInTheDocument();

    expect(screen.getByText("Treatment value: 1")).toBeInTheDocument();

    expect(screen.getByText("Control value: 0")).toBeInTheDocument();

    expect(screen.queryByLabelText("Treated unit")).not.toBeInTheDocument();
  }, 15_000);

  it("requires one treated unit and at least two non-overlapping donors for Synthetic Control", async () => {
    await moveToFilters(/Synthetic Control/i);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    const treatedUnit = await screen.findByLabelText("Treated unit");

    fireEvent.change(treatedUnit, {
      target: {
        value: "Boston",
      },
    });

    expect(
      screen.getByRole("checkbox", {
        name: "Donor Boston",
      }),
    ).toBeDisabled();

    const continueButton = screen.getByRole("button", {
      name: "Continue",
    });

    expect(continueButton).toBeDisabled();

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Donor Chicago",
      }),
    );

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Donor Austin",
      }),
    );

    expect(continueButton).toBeEnabled();
  });

  it("requires non-overlapping treated and control geographies for Geo Holdout", async () => {
    await moveToFilters(/Geo Holdout/i);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    const treatBoston = await screen.findByRole("checkbox", {
      name: "Treat geography Boston",
    });

    const controlBoston = screen.getByRole("checkbox", {
      name: "Control geography Boston",
    });

    fireEvent.click(treatBoston);

    expect(controlBoston).toBeDisabled();

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Control geography Chicago",
      }),
    );

    expect(
      screen.getByRole("button", {
        name: "Continue",
      }),
    ).toBeEnabled();
  });
  it("collects required Geo Holdout coordinates after geography assignment", async () => {
    await moveToFilters(/Geo Holdout/i);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.click(
      await screen.findByRole("checkbox", {
        name: "Treat geography Boston",
      }),
    );

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Control geography Chicago",
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Estimator settings",
      }),
    ).toBeInTheDocument();

    expect(screen.getByLabelText("Latitude Boston")).toHaveAttribute(
      "type",
      "number",
    );

    expect(screen.getByLabelText("Longitude Boston")).toHaveAttribute(
      "type",
      "number",
    );

    expect(screen.getByLabelText("Latitude Chicago")).toHaveAttribute(
      "type",
      "number",
    );

    expect(screen.getByLabelText("Longitude Chicago")).toHaveAttribute(
      "type",
      "number",
    );

    expect(screen.getByLabelText("Geo outcome kind")).toHaveValue("outcome");
  });

  it("shows backend-compatible MMM settings", async () => {
    await moveToFilters(/Marketing Mix Modeling/i);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Treatment and control setup",
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Estimator settings",
      }),
    ).toBeInTheDocument();

    expect(screen.getByLabelText("Seasonality period")).toHaveValue(52);

    expect(screen.getByLabelText("MMM outcome kind")).toHaveValue("revenue");

    expect(screen.getByLabelText("Adstock decay spend")).toHaveAttribute(
      "type",
      "number",
    );

    expect(
      screen.getByLabelText("Saturation half-spend spend"),
    ).toHaveAttribute("type", "number");
  });

  it("collects Off-policy assignment and supported estimator settings", async () => {
    await moveToFilters(/Off-policy Evaluation/i);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Treatment and control setup",
      }),
    ).toBeInTheDocument();

    const policyName = screen.getByLabelText("Policy name");

    const behaviorColumn = screen.getByLabelText("Behavior propensity column");

    const targetColumn = screen.getByLabelText("Target propensity column");

    const assignmentContinue = screen.getByRole("button", {
      name: "Continue",
    });

    expect(assignmentContinue).toBeDisabled();

    fireEvent.change(policyName, {
      target: {
        value: "growth_policy",
      },
    });

    fireEvent.change(behaviorColumn, {
      target: {
        value: "spend",
      },
    });

    fireEvent.change(targetColumn, {
      target: {
        value: "revenue",
      },
    });

    expect(assignmentContinue).toBeEnabled();

    fireEvent.click(assignmentContinue);

    expect(
      await screen.findByRole("heading", {
        name: "Estimator settings",
      }),
    ).toBeInTheDocument();

    const rewardColumn = screen.getByLabelText("Reward column");

    const expectedRewardColumn = screen.getByLabelText(
      "Expected reward column",
    );

    const primaryMethod = screen.getByLabelText("Primary method");

    expect(primaryMethod).toHaveValue("doubly_robust");

    expect(primaryMethod).toContainHTML(
      '<option value="importance_sampling">Importance sampling</option>',
    );

    expect(primaryMethod).toContainHTML(
      '<option value="self_normalized_importance_sampling">Self-normalized importance sampling</option>',
    );

    expect(primaryMethod).toContainHTML(
      '<option value="doubly_robust">Doubly robust</option>',
    );

    fireEvent.change(rewardColumn, {
      target: {
        value: "revenue",
      },
    });

    fireEvent.change(expectedRewardColumn, {
      target: {
        value: "spend",
      },
    });

    expect(
      screen.getByRole("button", {
        name: "Continue",
      }),
    ).toBeEnabled();
  });

  it("builds the analysis draft and shows a human-readable review before queueing", async () => {
    await moveToFilters(/Difference in Differences/i);

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

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Treatment and control setup",
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Estimator settings",
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Review analysis configuration",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("Difference in Differences")).toBeInTheDocument();

    expect(screen.getByText("2025-01-01 → 2025-03-31")).toBeInTheDocument();

    expect(screen.getByText("Intervention: 2025-02-01")).toBeInTheDocument();

    expect(screen.getByText("Treatment column: treated")).toBeInTheDocument();

    expect(screen.getByText("Treatment value: 1")).toBeInTheDocument();

    expect(screen.getByText("Control value: 0")).toBeInTheDocument();

    expect(screen.getByText("revenue · Greater than · 95")).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Queue analysis",
      }),
    ).toBeInTheDocument();
  });

  it("queues the reviewed analysis once and redirects to the returned run", async () => {
    const queuePromise = Promise.resolve({
      id: "run-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      estimator_type: "difference_in_differences",
      estimator_version: "did-v1",
      status: "queued",
    });

    queueAnalysisRunMock.mockReturnValue(queuePromise);

    await moveToFilters(/Difference in Differences/i);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Continue",
      }),
    );

    const queueButton = await screen.findByRole("button", {
      name: "Queue analysis",
    });

    fireEvent.click(queueButton);

    fireEvent.click(queueButton);

    await waitFor(() => {
      expect(queueAnalysisRunMock).toHaveBeenCalledTimes(1);
    });

    expect(queueButton).toBeDisabled();

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith(
        "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1",
      );
    });

    expect(queueAnalysisRunMock).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      expect.objectContaining({
        dataset_id: "dataset-1",
        semantic_mapping_version: 3,
        estimator_type: "difference_in_differences",
        configuration: expect.objectContaining({
          analysis_start_date: "2025-01-01",
          analysis_end_date: "2025-03-31",
          intervention_date: "2025-02-01",
        }),
      }),
    );
  });

  it("shows a human-readable queue error and allows retrying", async () => {
    queueAnalysisRunMock.mockRejectedValueOnce(
      new AnalysisRunApiError(
        "Dataset must be ready before an analysis can be queued.",
        409,
      ),
    );

    await moveToFilters(/Difference in Differences/i);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Continue",
      }),
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Continue",
      }),
    );

    const queueButton = await screen.findByRole("button", {
      name: "Queue analysis",
    });

    fireEvent.click(queueButton);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your analysis could not be queued because the dataset or configuration changed. Review the latest project data and try again.",
    );

    expect(
      screen.getByRole("link", {
        name: "Restart with latest data",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/analyses/new",
    );

    expect(queueButton).toBeEnabled();

    expect(pushMock).not.toHaveBeenCalled();
  });
});
