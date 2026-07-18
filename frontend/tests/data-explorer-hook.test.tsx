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
  fetchPreview,
  assessQuality,
  fetchDatasetVersions,
  getDataset,
} = vi.hoisted(() => ({
  fetchPreview: vi.fn(),
  assessQuality: vi.fn(),
  fetchDatasetVersions: vi.fn(),
  getDataset: vi.fn(),
}));

vi.mock("../src/lib/datasets/api", () => ({
  getDataset,
}));

vi.mock("../src/lib/data-products/api", () => ({
  fetchPreview,
  assessQuality,
  fetchDatasetVersions,
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

import { useDatasetExplorer } from "../src/lib/data-products/use-data-products";

describe("useDatasetExplorer refetch state", () => {
  beforeEach(() => {
    localStorage.setItem(
      "incrementality_session_token",
      "session-token",
    );

    fetchPreview.mockReset();
    assessQuality.mockReset();
    fetchDatasetVersions.mockReset();
    getDataset.mockReset();

    fetchPreview.mockResolvedValue({
      rows: [{ market: "Boston" }],
      columns: [],
      total_rows: 100,
      page: 1,
      page_size: 50,
      total_pages: 2,
      date_range: null,
      treatment_distribution: {},
      outcome_distribution: {},
    });

    assessQuality.mockResolvedValue({
      score: 100,
      ready: true,
      findings: [],
    });

    fetchDatasetVersions.mockResolvedValue([]);

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
      status: "ready",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:05:00Z",
      validation_started_at: "2026-07-18T12:06:00Z",
      validation_completed_at: "2026-07-18T12:07:00Z",
      row_count: 100,
      column_count: 1,
      failure_reason: null,
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("returns to loading while a new preview request is pending", async () => {
    const { result, rerender } = renderHook(
      ({ options }) =>
        useDatasetExplorer(
          "workspace-1",
          "project-1",
          "dataset-1",
          options,
          "difference_in_differences",
        ),
      {
        initialProps: {
          options: {
            page: 1,
            search: "",
            sortColumn: "",
            descending: false,
            filterColumn: "",
            filterValue: "",
          },
        },
      },
    );

    await waitFor(() => {
      expect(result.current.state.kind).toBe("ready");
    });

    fetchPreview.mockImplementationOnce(
      () => new Promise(() => undefined),
    );

    rerender({
      options: {
        page: 2,
        search: "",
        sortColumn: "",
        descending: false,
        filterColumn: "",
        filterValue: "",
      },
    });

    await waitFor(() => {
      expect(result.current.state.kind).toBe("loading");
    });
  });
});
