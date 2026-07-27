import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SESSION_TOKEN_KEY } from "../src/lib/auth/api";

const { getProjectOverviewMock, getDatasetMock, getLatestSemanticMappingMock } =
  vi.hoisted(() => ({
    getProjectOverviewMock: vi.fn(),
    getDatasetMock: vi.fn(),
    getLatestSemanticMappingMock: vi.fn(),
  }));

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

const baseProject = {
  id: "project-1",
  workspace_id: "workspace-1",
  created_by_user_id: "user-1",
  name: "Lift Study",
  slug: "lift-study",
  description: null,
  status: "active" as const,
  created_at: "2026-07-18T00:00:00Z",
  archived_at: null,
  latest_dataset_id: "dataset-1",
  latest_dataset_status: "ready",
  semantic_mapping_configured: true,
  latest_analysis_run_id: null,
  latest_analysis_run_status: null,
};

const readyDataset = {
  id: "dataset-1",
  workspace_id: "workspace-1",
  project_id: "project-1",
  created_by_user_id: "user-1",
  source_filename: "lift.csv",
  storage_key: "datasets/lift.csv",
  media_type: "text/csv",
  byte_size: 1000,
  checksum_sha256: "abc123",
  status: "ready" as const,
  created_at: "2026-07-18T00:00:00Z",
  uploaded_at: "2026-07-18T00:01:00Z",
  validation_started_at: "2026-07-18T00:02:00Z",
  validation_completed_at: "2026-07-18T00:03:00Z",
  row_count: 100,
  column_count: 8,
  failure_reason: null,
};

const mapping = {
  id: "mapping-1",
  dataset_id: "dataset-1",
  created_by_user_id: "user-1",
  version: 3,
  time_column: "date",
  unit_column: "geo",
  treatment_column: "treated",
  outcome_column: "revenue",
  spend_column: "spend",
  covariate_columns: ["seasonality"],
  treatment_value: "1",
  control_value: "0",
  created_at: "2026-07-18T00:04:00Z",
  updated_at: "2026-07-18T00:04:00Z",
};

describe("Analysis Configuration prerequisites", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    window.localStorage.setItem(SESSION_TOKEN_KEY, "session-token");

    getProjectOverviewMock.mockResolvedValue(baseProject);

    getDatasetMock.mockResolvedValue(readyDataset);

    getLatestSemanticMappingMock.mockResolvedValue(mapping);
  });

  afterEach(async () => {
    cleanup();

    await new Promise<void>((resolve) => {
      setImmediate(resolve);
    });
  });

  it("blocks configuration when the project has no dataset", async () => {
    getProjectOverviewMock.mockResolvedValue({
      ...baseProject,
      latest_dataset_id: null,
      latest_dataset_status: null,
      semantic_mapping_configured: false,
    });

    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText(
        "Upload a dataset before configuring an analysis.",
      ),
    ).toBeInTheDocument();

    expect(getDatasetMock).not.toHaveBeenCalled();
    expect(getLatestSemanticMappingMock).not.toHaveBeenCalled();
  });

  it("blocks configuration when the latest dataset is not ready", async () => {
    getDatasetMock.mockResolvedValue({
      ...readyDataset,
      status: "validating",
      validation_completed_at: null,
    });

    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText(
        "Your dataset must finish validation before you can configure an analysis.",
      ),
    ).toBeInTheDocument();

    expect(getLatestSemanticMappingMock).not.toHaveBeenCalled();
  });

  it("blocks configuration when semantic mapping is missing", async () => {
    getLatestSemanticMappingMock.mockResolvedValue(null);

    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText(
        "Configure semantic mapping before creating an analysis.",
      ),
    ).toBeInTheDocument();
  });

  it("allows configuration only for a ready scoped dataset with mapping", async () => {
    render(
      <AnalysisConfigurationClient
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText("Analysis configuration is ready to begin."),
    ).toBeInTheDocument();

    expect(getProjectOverviewMock).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
    );

    expect(getDatasetMock).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
    );

    expect(getLatestSemanticMappingMock).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
    );
  });
});
