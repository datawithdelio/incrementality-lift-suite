import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  AnalysisRunApiError,
  queueAnalysisRun,
} from "@/lib/analysis-configuration/api";

import type {
  QueueAnalysisRunRequest,
} from "@/lib/analysis-configuration/request";

const request:
  QueueAnalysisRunRequest = {
    dataset_id: "dataset-1",
    semantic_mapping_version: 3,
    estimator_type:
      "difference_in_differences",
    configuration: {
      analysis_start_date:
        "2025-01-01",
      analysis_end_date:
        "2025-03-31",
      intervention_date:
        "2025-02-01",
    },
  };

describe(
  "analysis configuration queue API",
  () => {
    afterEach(() => {
      vi.unstubAllGlobals();
    });

    it("queues an analysis run through the scoped project endpoint", async () => {
      const fetchMock = vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              id: "run-1",
              workspace_id:
                "workspace-1",
              project_id:
                "project-1",
              estimator_type:
                "difference_in_differences",
              status: "queued",
            }),
            {
              status: 201,
              headers: {
                "Content-Type":
                  "application/json",
              },
            },
          ),
      );

      vi.stubGlobal(
        "fetch",
        fetchMock,
      );

      const result =
        await queueAnalysisRun(
          "session-token",
          "workspace-1",
          "project-1",
          request,
        );

      expect(
        fetchMock,
      ).toHaveBeenCalledTimes(1);

      expect(
        fetchMock,
      ).toHaveBeenCalledWith(
        "/api/v1/workspaces/workspace-1/projects/project-1/analysis-runs",
        {
          method: "POST",
          headers: {
            Authorization:
              "Bearer session-token",
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify(
            request,
          ),
          cache: "no-store",
        },
      );

      expect(result.id).toBe(
        "run-1",
      );
    });

    it("preserves backend error detail and status for humanized UI handling", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(
          async () =>
            new Response(
              JSON.stringify({
                detail:
                  "Dataset must be ready before an analysis can be queued.",
              }),
              {
                status: 409,
                headers: {
                  "Content-Type":
                    "application/json",
                },
              },
            ),
        ),
      );

      try {
        await queueAnalysisRun(
          "session-token",
          "workspace-1",
          "project-1",
          request,
        );

        throw new Error(
          "Expected queueAnalysisRun to fail.",
        );
      } catch (error) {
        expect(
          error,
        ).toBeInstanceOf(
          AnalysisRunApiError,
        );

        expect(
          error,
        ).toMatchObject({
          status: 409,
          message:
            "Dataset must be ready before an analysis can be queued.",
        });
      }
    });

    it("returns a safe connection error when the request cannot reach the API", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(
          async () => {
            throw new TypeError(
              "Failed to fetch",
            );
          },
        ),
      );

      await expect(
        queueAnalysisRun(
          "session-token",
          "workspace-1",
          "project-1",
          request,
        ),
      ).rejects.toMatchObject({
        status: null,
        message:
          "We couldn't queue this analysis. Check your connection and try again.",
      });
    });
  },
);
