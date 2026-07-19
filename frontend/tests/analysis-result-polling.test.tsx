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
  fetchAnalysisResult,
} = vi.hoisted(() => ({
  fetchAnalysisResult: vi.fn(),
}));

vi.mock(
  "../src/lib/results/api",
  () => ({
    fetchAnalysisResult,

    ResultsApiError:
      class ResultsApiError
        extends Error {
        constructor(
          readonly status: number,
        ) {
          super(
            "Unable to retrieve analysis result.",
          );
        }
      },
  }),
);

import {
  useAnalysisResult,
} from "../src/lib/results/use-analysis-result";

const runningResult = {
  analysis_run_id: "run-1",
  workspace_id: "workspace-1",
  project_id: "project-1",
  run_status: "running",
  lifecycle_status: "running",
  estimator_type:
    "difference_in_differences",
  estimator_version: "did-v2",
  analysis_configuration: {},
  attempt_count: 1,
  max_attempts: 3,
  failure_information: null,
  result: null,
} as const;

describe(
  "useAnalysisResult polling",
  () => {
    beforeEach(() => {
      vi.useFakeTimers();

      localStorage.setItem(
        "incrementality_session_token",
        "session-token",
      );

      fetchAnalysisResult
        .mockReset();
    });

    afterEach(() => {
      vi.useRealTimers();
      localStorage.clear();
    });

    it(
      "preserves the last known running status when a polling refresh temporarily fails",
      async () => {
        fetchAnalysisResult
          .mockResolvedValueOnce(
            runningResult,
          )
          .mockRejectedValueOnce(
            new Error(
              "Temporary network failure",
            ),
          );

        const {
          result,
          unmount,
        } = renderHook(
          () =>
            useAnalysisResult(
              "workspace-1",
              "project-1",
              "run-1",
            ),
        );

        await act(
          async () => {
            await Promise.resolve();
            await Promise.resolve();
          },
        );

        expect(
          result.current.kind,
        ).toBe("ready");

        if (
          result.current.kind
          === "ready"
        ) {
          expect(
            result.current
              .data
              .lifecycle_status,
          ).toBe("running");
        }

        await act(
          async () => {
            await vi
              .advanceTimersByTimeAsync(
                3000,
              );
          },
        );

        expect(
          fetchAnalysisResult,
        ).toHaveBeenCalledTimes(2);

        expect(
          result.current.kind,
        ).toBe("ready");

        expect(
          result.current,
        ).toMatchObject({
          kind: "ready",
          refreshError: true,
        });

        if (
          result.current.kind
          === "ready"
        ) {
          expect(
            result.current
              .data
              .lifecycle_status,
          ).toBe("running");
        }

        unmount();
      },
    );

    it(
      "clears stale run state when switching analysis run ids",
      async () => {
        fetchAnalysisResult
          .mockResolvedValueOnce(
            runningResult,
          )
          .mockImplementationOnce(
            () =>
              new Promise(
                () => {
                  // Keep Run B pending so we can inspect
                  // the immediate transition state.
                },
              ),
          );

        const {
          result,
          rerender,
          unmount,
        } = renderHook(
          ({
            runId,
          }: {
            runId: string;
          }) =>
            useAnalysisResult(
              "workspace-1",
              "project-1",
              runId,
            ),
          {
            initialProps: {
              runId: "run-1",
            },
          },
        );

        await act(
          async () => {
            await Promise.resolve();
            await Promise.resolve();
          },
        );

        expect(
          result.current.kind,
        ).toBe("ready");

        rerender({
          runId: "run-2",
        });

        expect(
          result.current.kind,
        ).toBe("loading");

        expect(
          fetchAnalysisResult,
        ).toHaveBeenLastCalledWith(
          "workspace-1",
          "project-1",
          "run-2",
          "session-token",
          expect.any(AbortSignal),
        );

        unmount();
      },
    );

    it.each([
      "succeeded",
      "failed",
      "cancelled",
    ] as const)(
      "stops polling when the analysis becomes %s",
      async (terminalStatus) => {
        fetchAnalysisResult
          .mockResolvedValueOnce({
            ...runningResult,
            run_status:
              terminalStatus,
            lifecycle_status:
              terminalStatus,
          });

        const {
          result,
          unmount,
        } = renderHook(
          () =>
            useAnalysisResult(
              "workspace-1",
              "project-1",
              "run-1",
            ),
        );

        await act(
          async () => {
            await Promise.resolve();
            await Promise.resolve();
          },
        );

        expect(
          result.current.kind,
        ).toBe("ready");

        await act(
          async () => {
            await vi
              .advanceTimersByTimeAsync(
                12000,
              );
          },
        );

        expect(
          fetchAnalysisResult,
        ).toHaveBeenCalledTimes(1);

        unmount();
      },
    );

    it(
      "cleans up scheduled polling when the status page unmounts",
      async () => {
        fetchAnalysisResult
          .mockResolvedValue(
            runningResult,
          );

        const {
          unmount,
        } = renderHook(
          () =>
            useAnalysisResult(
              "workspace-1",
              "project-1",
              "run-1",
            ),
        );

        await act(
          async () => {
            await Promise.resolve();
            await Promise.resolve();
          },
        );

        expect(
          fetchAnalysisResult,
        ).toHaveBeenCalledTimes(1);

        unmount();

        await act(
          async () => {
            await vi
              .advanceTimersByTimeAsync(
                12000,
              );
          },
        );

        expect(
          fetchAnalysisResult,
        ).toHaveBeenCalledTimes(1);
      },
    );

  },
);
