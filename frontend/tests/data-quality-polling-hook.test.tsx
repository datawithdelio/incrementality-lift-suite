import {
  act,
  renderHook,
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

const validatingDataset = {
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
};

const readyDataset = {
  ...validatingDataset,
  status: "ready",
  validation_completed_at: "2026-07-18T12:07:00Z",
  row_count: 1537,
  column_count: 13,
};

describe("useDataQuality polling", () => {
  beforeEach(() => {
    vi.useFakeTimers();

    localStorage.setItem(
      "incrementality_session_token",
      "session-token",
    );

    getDataset.mockReset();
    assessQuality.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    localStorage.clear();
  });

  it("polls a validating dataset and automatically assesses quality when it becomes ready", async () => {
    getDataset
      .mockResolvedValueOnce(validatingDataset)
      .mockResolvedValueOnce(readyDataset);

    assessQuality.mockResolvedValue({
      score: 96,
      ready: true,
      findings: [],
    });

    const { result } = renderHook(() =>
      useDataQuality(
        "workspace-1",
        "project-1",
        "dataset-1",
        "difference_in_differences",
      ),
    );

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(getDataset).toHaveBeenCalledTimes(1);
    expect(result.current.dataset?.status).toBe("validating");
    expect(assessQuality).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(getDataset).toHaveBeenCalledTimes(2);
    expect(assessQuality).toHaveBeenCalledTimes(1);
    expect(result.current.dataset?.status).toBe("ready");
    expect(result.current.state.kind).toBe("ready");
  });
});
