import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock("../src/lib/data-products/use-data-products", () => ({
  useDatasetExplorer: vi.fn(() => ({
    state: {
      kind: "ready",
      data: {
        rows: [{ market: "Boston" }],
        columns: [],
        total_rows: 1537,
        page: 31,
        page_size: 50,
        total_pages: 31,
        date_range: null,
        treatment_distribution: {},
        outcome_distribution: {},
        visualizations: {
          time_column: "date",
          treatment_column: "treatment",
          outcome_column: "conversions",
          treatment_start_date: "2026-05-25",
          trend: [
            {
              period: "2026-01-05",
              treatment_value: 100,
              control_value: 90,
              treatment_observations: 1,
              control_observations: 1,
              phase: "pre",
            },
            {
              period: "2026-07-27",
              treatment_value: 120,
              control_value: 92,
              treatment_observations: 1,
              control_observations: 1,
              phase: "post",
            },
          ],
          distribution: {
            minimum: 90,
            maximum: 120,
            mean: 100.5,
            median: 96,
            first_quartile: 91,
            third_quartile: 110,
            outlier_count: 0,
            sample_size: 4,
            bins: [],
          },
          missingness: [],
          balance: null,
          breakdowns: {},
        },
      },
    },
    quality: undefined,
    versions: [],
    dataset: {
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
    },
  })),
}));

import { ExplorerClient } from "../src/components/data-products/data-product-clients";
import { useDatasetExplorer } from "../src/lib/data-products/use-data-products";

afterEach(() => {
  cleanup();
  localStorage.clear();
  window.history.replaceState(null, "", "/");
  vi.mocked(useDatasetExplorer).mockClear();
});

describe("ExplorerClient estimator state", () => {
  it("does not apply a detected date until the user confirms it", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(screen.getByLabelText("Intervention date")).toHaveValue("");
    expect(window.location.search).toBe("");
    expect(
      vi.mocked(useDatasetExplorer).mock.calls.every(
        (call) => call[3].interventionDate === "",
      ),
    ).toBe(true);

    fireEvent.click(
      screen.getByRole("button", { name: "Use detected date" }),
    );

    expect(window.location.search).toBe("?intervention=2026-05-25");
    expect(useDatasetExplorer).toHaveBeenLastCalledWith(
      "workspace-1",
      "project-1",
      "dataset-1",
      expect.objectContaining({ interventionDate: "2026-05-25" }),
      "difference_in_differences",
      expect.any(Function),
    );
  });

  it("initializes the explorer hook from an explicit valid URL date", () => {
    window.history.replaceState(null, "", "/?intervention=2026-05-25");

    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(useDatasetExplorer).toHaveBeenLastCalledWith(
      "workspace-1",
      "project-1",
      "dataset-1",
      expect.objectContaining({ interventionDate: "2026-05-25" }),
      "difference_in_differences",
      expect.any(Function),
    );
  });

  it("preserves the 2026 intervention date when switching to Synthetic Control", () => {
    window.history.replaceState(
      null,
      "",
      "/?intervention=2026-05-25",
    );

    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    fireEvent.change(
      screen.getByRole("combobox", {
        name: "Causal method",
      }),
      {
        target: {
          value: "synthetic_control",
        },
      },
    );

    expect(
      vi.mocked(useDatasetExplorer),
    ).toHaveBeenLastCalledWith(
      "workspace-1",
      "project-1",
      "dataset-1",
      expect.objectContaining({
        interventionDate: "2026-05-25",
      }),
      "synthetic_control",
      expect.any(Function),
    );
  });

  it("removes intervention UX and requests for Marketing Mix Modeling", () => {
    window.history.replaceState(null, "", "/?intervention=2026-05-25");

    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    const methodSelect = screen.getByRole("combobox", {
      name: "Causal method",
    });

    expect(methodSelect.closest(".explorer-evidence-controls")).not.toBeNull();
    expect(methodSelect.closest(".explorer-toolbar-main")).toBeNull();

    fireEvent.change(methodSelect, {
      target: { value: "marketing_mix_model" },
    });

    expect(screen.queryByLabelText("Intervention date")).not.toBeInTheDocument();
    expect(screen.queryByText("Selected intervention date")).not.toBeInTheDocument();
    expect(screen.queryByText("Pre-treatment")).not.toBeInTheDocument();
    expect(screen.queryByText("Post-treatment")).not.toBeInTheDocument();
    expect(screen.queryByText(/Treatment begins/)).not.toBeInTheDocument();
    expect(screen.queryByTestId("post-treatment-region")).not.toBeInTheDocument();
    expect(screen.getByText("Dataset start")).toBeInTheDocument();
    expect(screen.getByText("Dataset end")).toBeInTheDocument();
    const trendChart = screen.getByRole("group", {
      name: "Interactive trend chart",
    });
    expect(within(trendChart).queryByText("Treatment")).not.toBeInTheDocument();
    expect(within(trendChart).queryByText("Control")).not.toBeInTheDocument();
    expect(
      trendChart.querySelectorAll(".explorer-series-outcome"),
    ).toHaveLength(1);
    expect(
      trendChart.querySelectorAll(".explorer-series-treatment"),
    ).toHaveLength(0);
    expect(trendChart.querySelectorAll(".explorer-series-control")).toHaveLength(
      0,
    );

    fireEvent.mouseEnter(
      within(trendChart).getByRole("button", {
        name: /Inspect Jan 5, 2026\. Outcome 95/,
      }),
    );

    const periodSummary = screen.getByRole("region", {
      name: "Selected chart period",
    });
    expect(within(periodSummary).getByText("Outcome")).toBeInTheDocument();
    expect(within(periodSummary).getByText("95")).toBeInTheDocument();
    expect(within(periodSummary).getByText("Observations")).toBeInTheDocument();
    expect(within(periodSummary).queryByText("Treatment")).not.toBeInTheDocument();
    expect(within(periodSummary).queryByText("Control")).not.toBeInTheDocument();
    expect(within(periodSummary).queryByText("Difference")).not.toBeInTheDocument();
    expect(window.location.search).toBe("?estimator=marketing_mix_model");
    expect(
      window.localStorage.getItem(
        "incrementality_dataset_estimator_dataset-1",
      ),
    ).toBe("marketing_mix_model");
    expect(
      screen.getByRole("link", { name: "Semantic Mapping" }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/mapping?estimator=marketing_mix_model",
    );
    expect(useDatasetExplorer).toHaveBeenLastCalledWith(
      "workspace-1",
      "project-1",
      "dataset-1",
      expect.objectContaining({ interventionDate: "" }),
      "marketing_mix_model",
      expect.any(Function),
    );

    fireEvent.change(
      screen.getByRole("combobox", { name: "Causal method" }),
      { target: { value: "geo_holdout" } },
    );

    expect(screen.getByLabelText("Intervention date")).toHaveValue(
      "2026-05-25",
    );
    expect(
      trendChart.querySelector('[data-series="treatment"]'),
    ).toHaveTextContent("Treatment");
    expect(
      trendChart.querySelector('[data-series="control"]'),
    ).toHaveTextContent("Control");
    expect(
      trendChart.querySelectorAll(".explorer-series-treatment"),
    ).toHaveLength(1);
    expect(trendChart.querySelectorAll(".explorer-series-control")).toHaveLength(
      1,
    );
    expect(useDatasetExplorer).toHaveBeenLastCalledWith(
      "workspace-1",
      "project-1",
      "dataset-1",
      expect.objectContaining({ interventionDate: "2026-05-25" }),
      "geo_holdout",
      expect.any(Function),
    );
  });

  it("commits the latest date before switching to Synthetic Control", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    const interventionInput = screen.getByLabelText("Intervention date");

    for (const intermediateValue of [
      "0002-05-25",
      "0020-05-25",
      "0202-05-25",
    ]) {
      fireEvent.focus(interventionInput);
      fireEvent.change(interventionInput, {
        target: { value: intermediateValue },
      });
      fireEvent.blur(interventionInput);
    }

    expect(
      vi.mocked(useDatasetExplorer).mock.calls.map((call) =>
        call[3].interventionDate,
      ),
    ).toEqual([""]);

    fireEvent.focus(interventionInput);
    fireEvent.change(interventionInput, {
      target: { value: "2026-05-25" },
    });

    // Native browser interaction blurs the date field before the
    // causal-method select receives the click/change.
    fireEvent.blur(interventionInput);

    fireEvent.change(
      screen.getByRole("combobox", { name: "Causal method" }),
      { target: { value: "synthetic_control" } },
    );

    expect(window.location.search).toBe("?intervention=2026-05-25");
    expect(useDatasetExplorer).toHaveBeenLastCalledWith(
      "workspace-1",
      "project-1",
      "dataset-1",
      expect.objectContaining({ interventionDate: "2026-05-25" }),
      "synthetic_control",
      expect.any(Function),
    );

    const interventionDates = vi
      .mocked(useDatasetExplorer)
      .mock.calls.map((call) => call[3].interventionDate);
    expect(interventionDates).not.toContain("2025-05-25");
    expect(interventionDates).not.toContain("2025-07-25");
  });
});

describe("ExplorerClient", () => {
  it("passes restored backend dataset metadata into the Explorer", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(screen.getByText("campaign-results.csv")).toBeInTheDocument();

    expect(screen.getByText("1,537")).toBeInTheDocument();
    expect(screen.getByText("13")).toBeInTheDocument();

    expect(
      screen.queryByText("private/storage/path.csv"),
    ).not.toBeInTheDocument();
  });
});

describe("ExplorerClient dataset navigation", () => {
  it("links to the correctly scoped Data Quality page", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByRole("link", {
        name: "View Data Quality",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/quality",
    );
  });
});

describe("ExplorerClient pagination", () => {
  it("disables Next when the backend reports the final page", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByRole("button", {
        name: "Next",
      }),
    ).toBeDisabled();
  });
});

describe("ExplorerClient premium structure", () => {
  it("groups the explorer identity and controls for fast scanning", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(screen.getByText("Measurement evidence")).toBeInTheDocument();

    expect(
      screen.getByRole("region", {
        name: "Explore dataset controls",
      }),
    ).toBeInTheDocument();
  });
});

describe("ExplorerClient premium information order", () => {
  it("places the dataset overview before the exploration toolbar", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    const summary = screen.getByRole("region", {
      name: "Dataset summary",
    });

    const controls = screen.getByRole("region", {
      name: "Explore dataset controls",
    });

    expect(
      summary.compareDocumentPosition(controls) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});

describe("ExplorerClient saved views", () => {
  it("saves the current exploration settings under a user-defined name", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    fireEvent.change(
      screen.getByRole("textbox", {
        name: "Saved view name",
      }),
      {
        target: {
          value: "Missing revenue review",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Save current view",
      }),
    );

    expect(
      screen.getByRole("option", {
        name: "Missing revenue review",
      }),
    ).toBeInTheDocument();
  });
});
