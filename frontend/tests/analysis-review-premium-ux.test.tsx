import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SESSION_TOKEN_KEY } from "../src/lib/auth/api";

import type { AnalysisConfigurationDraft } from "../src/lib/analysis-configuration/request";

const { pushMock, queueAnalysisRunMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  queueAnalysisRunMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("../src/lib/analysis-configuration/api", async () => {
  const actual = await vi.importActual<
    typeof import("../src/lib/analysis-configuration/api")
  >("../src/lib/analysis-configuration/api");

  return {
    ...actual,
    queueAnalysisRun: queueAnalysisRunMock,
  };
});

import { AnalysisConfigurationReview } from "../src/components/analysis-configuration/analysis-configuration-review";

const draft: AnalysisConfigurationDraft = {
  estimatorType: "difference_in_differences",

  period: {
    analysisStartDate: "2025-01-01",
    analysisEndDate: "2025-03-31",
    interventionDate: "2025-02-01",
  },

  selection: {
    rowFilters: [
      {
        column: "revenue",
        operator: "greater_than",
        value: {
          type: "number",
          value: 95,
        },
      },
    ],

    selectedGeographies: ["Boston"],

    excludedGeographies: [],

    segmentColumn: "",

    selectedSegments: [],

    excludedSegments: [],
  },

  treatmentControl: {
    kind: "mapped_binary",
  },

  settings: {
    kind: "difference_in_differences",
  },
};

function renderReview() {
  render(
    <AnalysisConfigurationReview
      draft={draft}
      mappingTreatment={{
        column: "treated",
        treatmentValue: "1",
        controlValue: "0",
      }}
      workspaceId="workspace-1"
      projectId="project-1"
      datasetId="dataset-1"
      semanticMappingVersion={3}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();

  window.localStorage.setItem(SESSION_TOKEN_KEY, "session-token");
});

afterEach(() => {
  cleanup();
});

describe("premium analysis review", () => {
  it("shows the complete human-readable configuration and exact request", () => {
    renderReview();

    expect(
      screen.getByRole("heading", {
        name: "Review analysis configuration",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("Difference in Differences")).toBeInTheDocument();

    expect(screen.getByText("2025-01-01 → 2025-03-31")).toBeInTheDocument();

    expect(screen.getByText("Intervention: 2025-02-01")).toBeInTheDocument();

    expect(screen.getByText("Treatment column: treated")).toBeInTheDocument();

    expect(screen.getByText("revenue · Greater than · 95")).toBeInTheDocument();

    expect(screen.getByText("Exact queue request")).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Queue analysis",
      }),
    ).toBeEnabled();
  });

  it("queues the exact reviewed configuration once", async () => {
    queueAnalysisRunMock.mockResolvedValue({
      id: "run-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      estimator_type: "difference_in_differences",
      estimator_version: "did-v1",
      status: "queued",
    });

    renderReview();

    const queueButton = screen.getByRole("button", {
      name: "Queue analysis",
    });

    fireEvent.click(queueButton);
    fireEvent.click(queueButton);

    await waitFor(() => {
      expect(queueAnalysisRunMock).toHaveBeenCalledTimes(1);
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

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith(
        "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1",
      );
    });
  });
});
