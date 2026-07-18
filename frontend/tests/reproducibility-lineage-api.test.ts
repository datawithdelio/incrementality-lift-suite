import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchAnalysisLineage,
  ResultsApiError,
} from "../src/lib/results/api";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("fetchAnalysisLineage", () => {
  it("fetches the persisted lineage endpoint with authentication", async () => {
    const payload = {
      analysis_run_id: "run-1",
      dataset_id: "dataset-1",
      dataset_checksum_sha256: "b".repeat(64),
      dataset_byte_size: 4096,
      semantic_mapping_id: "mapping-1",
      semantic_mapping_version: 3,
      semantic_mapping_snapshot: null,
      analysis_period_snapshot: null,
      analysis_selection_snapshot: null,
      treatment_control_snapshot: null,
      estimand_snapshot: null,
      estimator_type: "difference_in_differences",
      estimator_version: "did-v2",
      estimator_configuration: {},
      random_seed: 1729,
      application_version: "0.1.0",
      source_revision: "c".repeat(40),
      statistical_library_versions: null,
      input_fingerprint_sha256: "a".repeat(64),
      created_at: "2026-07-17T20:00:00Z",
    };

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify(payload),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json",
            },
          },
        ),
      );

    const controller = new AbortController();

    const result = await fetchAnalysisLineage(
      "workspace-1",
      "project-1",
      "run-1",
      "session-token",
      controller.signal,
    );

    expect(result).toEqual(payload);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects/project-1/analysis-runs/run-1/lineage",
      {
        headers: {
          Authorization: "Bearer session-token",
        },
        signal: controller.signal,
        cache: "no-store",
      },
    );
  });

  it("preserves HTTP status through ResultsApiError", async () => {
    vi.spyOn(
      globalThis,
      "fetch",
    ).mockResolvedValue(
      new Response(
        null,
        {
          status: 404,
        },
      ),
    );

    await expect(
      fetchAnalysisLineage(
        "workspace-1",
        "project-1",
        "missing-run",
        "session-token",
      ),
    ).rejects.toMatchObject({
      status: 404,
    } satisfies Partial<ResultsApiError>);
  });
});
