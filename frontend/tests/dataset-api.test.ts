import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getDataset,
  registerDataset,
  uploadDatasetContent,
} from "../src/lib/datasets/api";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("dataset API", () => {
  it("registers dataset metadata in the correct workspace and project scope", async () => {
    const response = {
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private-storage-key",
      media_type: "text/csv",
      byte_size: 128,
      checksum_sha256: "a".repeat(64),
      status: "pending_upload",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: null,
      validation_started_at: null,
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    };

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const result = await registerDataset(
      "session-token",
      "workspace-1",
      "project-1",
      {
        source_filename: "campaign-results.csv",
        media_type: "text/csv",
        byte_size: 128,
        checksum_sha256: "a".repeat(64),
      },
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects/project-1/datasets",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer session-token",
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({
          source_filename: "campaign-results.csv",
          media_type: "text/csv",
          byte_size: 128,
          checksum_sha256: "a".repeat(64),
        }),
      }),
    );

    expect(result).toEqual(response);
  });

  it("uploads the CSV bytes to the registered dataset content endpoint", async () => {
    const response = {
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private-storage-key",
      media_type: "text/csv",
      byte_size: 30,
      checksum_sha256: "a".repeat(64),
      status: "uploaded",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: null,
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    };

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const file = new File(
      ["date,revenue\n2026-07-01,100\n"],
      "campaign-results.csv",
      { type: "text/csv" },
    );

    const result = await uploadDatasetContent(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
      file,
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects/project-1/datasets/dataset-1/content",
      expect.objectContaining({
        method: "PUT",
        headers: expect.objectContaining({
          Authorization: "Bearer session-token",
          "Content-Type": "text/csv",
        }),
        body: file,
      }),
    );

    expect(result.status).toBe("uploaded");
  });



  it("reloads a dataset from the correct workspace and project scope", async () => {
    const response = {
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private-storage-key",
      media_type: "text/csv",
      byte_size: 30,
      checksum_sha256: "a".repeat(64),
      status: "validating",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    };

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const result = await getDataset(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects/project-1/datasets/dataset-1",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer session-token",
        }),
      }),
    );

    expect(result.status).toBe("validating");
  });


});
