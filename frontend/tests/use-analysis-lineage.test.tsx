import {
  act,
  renderHook,
  waitFor,
} from "@testing-library/react";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  fetchAnalysisLineage,
} from "../src/lib/results/api";
import {
  useAnalysisLineage,
} from "../src/lib/results/use-analysis-lineage";

vi.mock(
  "../src/lib/results/api",
  async () => {
    const actual = await vi.importActual<
      typeof import("../src/lib/results/api")
    >("../src/lib/results/api");

    return {
      ...actual,
      fetchAnalysisLineage: vi.fn(),
    };
  },
);

const mockedFetchAnalysisLineage =
  vi.mocked(fetchAnalysisLineage);

const lineageA = {
  analysis_run_id: "run-a",
  dataset_id: "dataset-a",
  dataset_checksum_sha256:
    "a".repeat(64),
  dataset_byte_size: 100,
  semantic_mapping_id: "mapping-a",
  semantic_mapping_version: 1,
  semantic_mapping_snapshot: null,
  analysis_period_snapshot: null,
  analysis_selection_snapshot: null,
  treatment_control_snapshot: null,
  estimand_snapshot: null,
  estimator_type:
    "difference_in_differences",
  estimator_version: "did-v1",
  estimator_configuration: {},
  random_seed: 1,
  application_version: "0.1.0",
  source_revision: "a".repeat(40),
  statistical_library_versions: null,
  input_fingerprint_sha256:
    "1".repeat(64),
  created_at:
    "2026-07-17T20:00:00Z",
};

const lineageB = {
  ...lineageA,
  analysis_run_id: "run-b",
  dataset_id: "dataset-b",
  dataset_checksum_sha256:
    "b".repeat(64),
  input_fingerprint_sha256:
    "2".repeat(64),
};

beforeEach(() => {
  vi.clearAllMocks();

  window.localStorage.setItem(
    "incrementality_session_token",
    "session-token",
  );
});

describe(
  "useAnalysisLineage",
  () => {
    it(
      "clears stale lineage immediately when the run scope changes",
      async () => {
        let resolveRunB:
          | ((value: typeof lineageB) => void)
          | undefined;

        mockedFetchAnalysisLineage
          .mockResolvedValueOnce(
            lineageA,
          )
          .mockImplementationOnce(
            () =>
              new Promise(
                (resolve) => {
                  resolveRunB =
                    resolve;
                },
              ),
          );

        const {
          result,
          rerender,
        } = renderHook(
          ({
            workspaceId,
            projectId,
            analysisRunId,
          }) =>
            useAnalysisLineage(
              workspaceId,
              projectId,
              analysisRunId,
            ),
          {
            initialProps: {
              workspaceId:
                "workspace-1",
              projectId:
                "project-1",
              analysisRunId:
                "run-a",
            },
          },
        );

        await waitFor(() => {
          expect(
            result.current.kind,
          ).toBe("ready");
        });

        if (
          result.current.kind
          !== "ready"
        ) {
          throw new Error(
            "Expected Run A lineage to load.",
          );
        }

        expect(
          result.current.data
            .analysis_run_id,
        ).toBe("run-a");

        rerender({
          workspaceId:
            "workspace-1",
          projectId:
            "project-1",
          analysisRunId:
            "run-b",
        });

        expect(
          result.current,
        ).toEqual({
          kind: "loading",
        });

        await waitFor(() => {
          expect(
            mockedFetchAnalysisLineage,
          ).toHaveBeenLastCalledWith(
            "workspace-1",
            "project-1",
            "run-b",
            "session-token",
            expect.any(
              AbortSignal,
            ),
          );
        });

        await act(
          async () => {
            resolveRunB?.(
              lineageB,
            );
          },
        );

        await waitFor(() => {
          expect(
            result.current.kind,
          ).toBe("ready");
        });

        if (
          result.current.kind
          !== "ready"
        ) {
          throw new Error(
            "Expected Run B lineage to load.",
          );
        }

        expect(
          result.current.data
            .analysis_run_id,
        ).toBe("run-b");

        expect(
          result.current.data
            .dataset_checksum_sha256,
        ).toBe(
          "b".repeat(64),
        );
      },
    );
  },
);
