import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { ReportHistory } from "../src/components/data-products/report-history";

const {
  downloadReport,
} = vi.hoisted(() => ({
  downloadReport: vi.fn(),
}));

vi.mock(
  "../src/lib/data-products/api",
  () => ({
    downloadReport,
  }),
);

const succeededReport = {
  id: "report-1",
  version: 2,
  format: "pdf",
  status: "succeeded",
  attempt_count: 1,
  max_attempts: 3,
  failure_reason: null,
  created_at: "2026-07-19T16:00:00Z",
};

beforeEach(() => {
  localStorage.setItem(
    "incrementality_session_token",
    "session-token",
  );

  downloadReport.mockReset();
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});

describe(
  "ReportHistory download",
  () => {
    it(
      "uses the authorized download API and shows an in-flight state",
      () => {
        downloadReport.mockImplementation(
          () =>
            new Promise(
              () => {
                // Keep download pending so the loading
                // state can be inspected.
              },
            ),
        );

        render(
          <ReportHistory
            reports={[
              succeededReport,
            ]}
            workspaceId="workspace-1"
            projectId="project-1"
            runId="run-1"
          />,
        );

        const downloadButton =
          screen.getByRole(
            "button",
            {
              name: "Download",
            },
          );

        fireEvent.click(
          downloadButton,
        );

        expect(
          downloadReport,
        ).toHaveBeenCalledTimes(1);

        expect(
          downloadReport,
        ).toHaveBeenCalledWith(
          "workspace-1",
          "project-1",
          "run-1",
          "report-1",
          "session-token",
        );

        expect(
          downloadButton,
        ).toBeDisabled();

        expect(
          screen.getByText(
            "Downloading…",
          ),
        ).toBeInTheDocument();
      },
    );

    it(
      "saves the downloaded blob with the server-controlled filename",
      async () => {
        const blob = new Blob(
          ["report"],
          {
            type: "application/pdf",
          },
        );

        downloadReport.mockResolvedValue({
          blob,
          filename:
            "analysis-report-v2.pdf",
        });

        const createObjectURL = vi.fn(
          () => "blob:report-download",
        );

        const revokeObjectURL = vi.fn();

        Object.defineProperty(
          URL,
          "createObjectURL",
          {
            configurable: true,
            value: createObjectURL,
          },
        );

        Object.defineProperty(
          URL,
          "revokeObjectURL",
          {
            configurable: true,
            value: revokeObjectURL,
          },
        );

        const clickSpy = vi
          .spyOn(
            HTMLAnchorElement.prototype,
            "click",
          )
          .mockImplementation(
            () => undefined,
          );

        render(
          <ReportHistory
            reports={[
              succeededReport,
            ]}
            workspaceId="workspace-1"
            projectId="project-1"
            runId="run-1"
          />,
        );

        fireEvent.click(
          screen.getByRole(
            "button",
            {
              name: "Download",
            },
          ),
        );

        await waitFor(() => {
          expect(
            createObjectURL,
          ).toHaveBeenCalledWith(
            blob,
          );
        });

        expect(
          clickSpy,
        ).toHaveBeenCalledTimes(1);

        expect(
          revokeObjectURL,
        ).toHaveBeenCalledWith(
          "blob:report-download",
        );
      },
    );

    it(
      "shows a safe retry state when a download fails",
      async () => {
        downloadReport.mockRejectedValueOnce(
          new Error(
            "raw storage provider failure",
          ),
        );

        render(
          <ReportHistory
            reports={[
              succeededReport,
            ]}
            workspaceId="workspace-1"
            projectId="project-1"
            runId="run-1"
          />,
        );

        fireEvent.click(
          screen.getByRole(
            "button",
            {
              name: "Download",
            },
          ),
        );

        expect(
          await screen.findByRole(
            "alert",
          ),
        ).toHaveTextContent(
          "Download failed. Please try again.",
        );

        expect(
          screen.queryByText(
            "raw storage provider failure",
          ),
        ).not.toBeInTheDocument();

        expect(
          screen.getByRole(
            "button",
            {
              name: "Try Download Again",
            },
          ),
        ).toBeEnabled();
      },
    );
  },
);
