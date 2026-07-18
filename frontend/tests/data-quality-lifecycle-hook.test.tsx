import { renderHook, waitFor } from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const {
  getDataset,
  assessQuality,
} = vi.hoisted(() => ({
  getDataset: vi.fn(),
  assessQuality: vi.fn(),
}));

vi.mock("../src/lib/datasets/api", () => ({
  getDataset,
}));

vi.mock("../src/lib/data-products/api", () => ({
  assessQuality,
  fetchDatasetVersions: vi.fn(),
  fetchPreview: vi.fn(),
  fetchReports: vi.fn(),
  DataProductApiError: class DataProductApiError extends Error {
    constructor(
      message: string,
      readonly status: number,
    ) {
      super(message);
    }
  },
}));

import { useDataQuality } from "../src/lib/data-products/use-data-products";

describe("useDataQuality dataset lifecycle", () => {
  beforeEach(() => {
    localStorage.setItem(
      "incrementality_session_token",
      "session-token",
    );

    getDataset.mockReset();
    assessQuality.mockReset();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("does not assess quality while dataset validation is running", async () => {
    getDataset.mockResolvedValue({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private/path.csv",
      media_type: "text/csv",
      byte_size: 2048,
      checksum_sha256: "a".repeat(64),
      status: "validating",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:05:00Z",
      validation_started_at: "2026-07-18T12:06:00Z",
      validation_completed_at: null,
      row_count: null,
      column_count: null,
      failure_reason: null,
    });

    const { result } = renderHook(() =>
      useDataQuality(
        "workspace-1",
        "project-1",
        "dataset-1",
        "difference_in_differences",
      ),
    );

    await waitFor(() => {
      expect(result.current.dataset?.status).toBe(
        "validating",
      );
    });

    expect(assessQuality).not.toHaveBeenCalled();
  });

  it("preserves the backend validation failure reason", async () => {
    getDataset.mockResolvedValue({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "campaign-results.csv",
      storage_key: "private/path.csv",
      media_type: "text/csv",
      byte_size: 2048,
      checksum_sha256: "a".repeat(64),
      status: "failed",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:05:00Z",
      validation_started_at: "2026-07-18T12:06:00Z",
      validation_completed_at: "2026-07-18T12:07:00Z",
      row_count: null,
      column_count: null,
      failure_reason:
        "The uploaded CSV has inconsistent column counts.",
    });

    const { result } = renderHook(() =>
      useDataQuality(
        "workspace-1",
        "project-1",
        "dataset-1",
        "difference_in_differences",
      ),
    );

    await waitFor(() => {
      expect(result.current.dataset?.failure_reason).toBe(
        "The uploaded CSV has inconsistent column counts.",
      );
    });

    expect(assessQuality).not.toHaveBeenCalled();
  });
});
