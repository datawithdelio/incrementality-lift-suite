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
  fetchReports,
} = vi.hoisted(() => ({
  fetchReports: vi.fn(),
}));

vi.mock(
  "../src/lib/data-products/api",
  () => ({
    fetchReports,

    DataProductApiError:
      class DataProductApiError
        extends Error {
        constructor(
          readonly status: number,
        ) {
          super(
            "Data product is unavailable.",
          );
        }
      },
  }),
);

import {
  useReports,
} from "../src/lib/data-products/use-data-products";

const pendingReport = {
  id: "report-1",
  version: 1,
  format: "pdf",
  status: "pending",
  attempt_count: 0,
  max_attempts: 3,
  failure_reason: null,
  created_at: "2026-07-19T12:00:00Z",
};

const succeededReport = {
  ...pendingReport,
  status: "succeeded",
};

describe(
  "useReports polling",
  () => {
    beforeEach(() => {
      vi.useFakeTimers();

      localStorage.setItem(
        "incrementality_session_token",
        "session-token",
      );

      fetchReports.mockReset();
    });

    afterEach(() => {
      vi.useRealTimers();
      localStorage.clear();
    });

    it(
      "polls again while a report is pending",
      async () => {
        fetchReports
          .mockResolvedValueOnce([
            pendingReport,
          ])
          .mockResolvedValueOnce([
            succeededReport,
          ]);

        const {
          result,
          unmount,
        } = renderHook(
          () =>
            useReports(
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
          result.current,
        ).toMatchObject({
          kind: "ready",
          data: [
            {
              id: "report-1",
              status: "pending",
            },
          ],
        });

        expect(
          fetchReports,
        ).toHaveBeenCalledTimes(1);

        await act(
          async () => {
            await vi
              .advanceTimersByTimeAsync(
                3000,
              );
          },
        );

        expect(
          fetchReports,
        ).toHaveBeenCalledTimes(2);

        expect(
          result.current,
        ).toMatchObject({
          kind: "ready",
          data: [
            {
              id: "report-1",
              status: "succeeded",
            },
          ],
        });

        unmount();
      },
    );

    it.each([
      "succeeded",
      "failed",
    ])(
      "stops polling when all reports are %s",
      async (terminalStatus) => {
        fetchReports.mockResolvedValueOnce([
          {
            ...pendingReport,
            status: terminalStatus,
          },
        ]);

        const {
          result,
          unmount,
        } = renderHook(
          () =>
            useReports(
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
          fetchReports,
        ).toHaveBeenCalledTimes(1);

        unmount();
      },
    );

    it(
      "clears stale report history when switching analysis runs",
      async () => {
        fetchReports
          .mockResolvedValueOnce([
            {
              ...succeededReport,
              id: "run-a-report",
            },
          ])
          .mockImplementationOnce(
            () =>
              new Promise(
                () => {
                  // Keep Run B loading so the immediate
                  // transition state can be inspected.
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
            useReports(
              "workspace-1",
              "project-1",
              runId,
            ),
          {
            initialProps: {
              runId: "run-a",
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
          result.current,
        ).toMatchObject({
          kind: "ready",
          data: [
            {
              id: "run-a-report",
            },
          ],
        });

        rerender({
          runId: "run-b",
        });

        expect(
          result.current.kind,
        ).toBe("loading");

        expect(
          fetchReports,
        ).toHaveBeenLastCalledWith(
          "workspace-1",
          "project-1",
          "run-b",
          "session-token",
          expect.any(AbortSignal),
        );

        unmount();
      },
    );

    it(
      "preserves the last known report state and retries after a temporary polling failure",
      async () => {
        fetchReports
          .mockResolvedValueOnce([
            pendingReport,
          ])
          .mockRejectedValueOnce(
            new TypeError(
              "temporary network failure",
            ),
          )
          .mockResolvedValueOnce([
            succeededReport,
          ]);

        const {
          result,
          unmount,
        } = renderHook(
          () =>
            useReports(
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
          result.current,
        ).toMatchObject({
          kind: "ready",
          data: [
            {
              status: "pending",
            },
          ],
        });

        await act(
          async () => {
            await vi
              .advanceTimersByTimeAsync(
                3000,
              );
          },
        );

        expect(
          result.current,
        ).toMatchObject({
          kind: "ready",
          data: [
            {
              status: "pending",
            },
          ],
        });

        await act(
          async () => {
            await vi
              .advanceTimersByTimeAsync(
                3000,
              );
          },
        );

        expect(
          fetchReports,
        ).toHaveBeenCalledTimes(3);

        expect(
          result.current,
        ).toMatchObject({
          kind: "ready",
          data: [
            {
              status: "succeeded",
            },
          ],
        });

        unmount();
      },
    );
  },
);
