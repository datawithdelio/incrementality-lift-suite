import {
  cleanup,
  render,
  screen,
} from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const {
  getDatasetMock,
} = vi.hoisted(() => ({
  getDatasetMock: vi.fn(),
}));

vi.mock(
  "../src/lib/datasets/api",
  async () => {
    const actual = await vi.importActual<
      typeof import("../src/lib/datasets/api")
    >("../src/lib/datasets/api");

    return {
      ...actual,
      getDataset: getDatasetMock,
    };
  },
);

import { SemanticMappingClient } from "../src/components/semantic-mapping/semantic-mapping-client";

describe("semantic mapping dataset readiness", () => {
  beforeEach(() => {
    getDatasetMock.mockReset();

    window.localStorage.setItem(
      "incrementality_session_token",
      "session-token",
    );

    getDatasetMock.mockResolvedValue({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "experiment.csv",
      storage_key: "datasets/experiment.csv",
      media_type: "text/csv",
      byte_size: 100,
      checksum_sha256: "abc123",
      status: "validating",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    });
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it("blocks mapping while the scoped dataset is still validating", async () => {
    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "This dataset is still being validated. Mapping will be available when validation completes.",
    );

    expect(getDatasetMock).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
    );
  });

  it("blocks mapping when the dataset upload has not completed", async () => {
    getDatasetMock.mockResolvedValue({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "experiment.csv",
      storage_key: "datasets/experiment.csv",
      media_type: "text/csv",
      byte_size: 100,
      checksum_sha256: "abc123",
      status: "pending_upload",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: null,
      validation_started_at: null,
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    });

    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "This dataset upload has not completed. Mapping will be available after the upload and validation finish.",
    );
  });


  it("blocks mapping while an uploaded dataset is waiting for validation", async () => {
    getDatasetMock.mockResolvedValue({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "experiment.csv",
      storage_key: "datasets/experiment.csv",
      media_type: "text/csv",
      byte_size: 100,
      checksum_sha256: "abc123",
      status: "uploaded",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: null,
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    });

    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "This dataset is waiting for validation. Mapping will be available when validation completes.",
    );
  });


  it("blocks mapping when dataset validation failed", async () => {
    getDatasetMock.mockResolvedValue({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "experiment.csv",
      storage_key: "datasets/experiment.csv",
      media_type: "text/csv",
      byte_size: 100,
      checksum_sha256: "abc123",
      status: "failed",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: "2026-07-18T12:03:00Z",
      row_count: null,
      column_count: null,
      failure_reason: "Required columns could not be validated.",
    });

    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "This dataset failed validation. Correct the dataset before configuring semantic mapping.",
    );
  });

});
