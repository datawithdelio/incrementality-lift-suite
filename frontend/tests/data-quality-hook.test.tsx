import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as dataProductHooks from "../src/lib/data-products/use-data-products";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("useDataQuality", () => {
  it("loads the scoped ready dataset before the scoped quality assessment", async () => {
    localStorage.setItem(
      "incrementality_session_token",
      "session-token",
    );

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
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
            row_count: 1537,
            column_count: 13,
            failure_reason: null,
          }),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json",
            },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            score: 82,
            ready: true,
            findings: [],
          }),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json",
            },
          },
        ),
      );

    const hooks = dataProductHooks as typeof dataProductHooks & {
      useDataQuality?: (
        workspaceId: string,
        projectId: string,
        datasetId: string,
        estimator: string,
      ) => {
        state: {
          kind: string;
        };
      };
    };

    expect(hooks.useDataQuality).toBeTypeOf("function");

    const { result } = renderHook(() =>
      hooks.useDataQuality?.(
        "workspace-1",
        "project-1",
        "dataset-1",
        "difference_in_differences",
      ),
    );

    await waitFor(() => {
      expect(result.current?.state.kind).toBe("ready");
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/workspaces/workspace-1/projects/project-1/datasets/dataset-1",
      expect.objectContaining({
        method: "GET",
        cache: "no-store",
      }),
    );

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining(
        "/api/v1/workspaces/workspace-1/projects/project-1/datasets/dataset-1/quality?estimator=difference_in_differences",
      ),
      expect.objectContaining({
        method: "POST",
      }),
    );
  });
});
