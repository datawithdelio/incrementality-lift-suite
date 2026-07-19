import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReportsClient } from "../src/components/data-products/data-product-clients";
import { useReports } from "../src/lib/data-products/use-data-products";
import { useAnalysisResult } from "../src/lib/results/use-analysis-result";

vi.mock("../src/lib/data-products/use-data-products", () => ({
  useReports: vi.fn(),
}));


vi.mock("../src/lib/results/use-analysis-result", () => ({
  useAnalysisResult: vi.fn(),
}));

const {
  queueReport,
} = vi.hoisted(() => ({
  queueReport: vi.fn(),
}));

vi.mock("../src/lib/data-products/api", () => ({
  queueReport,
}));

const mockedUseReports = vi.mocked(useReports);

const mockedUseAnalysisResult =
  vi.mocked(useAnalysisResult);

beforeEach(() => {
  localStorage.setItem(
    "incrementality_session_token",
    "session-token",
  );

  mockedUseReports.mockReturnValue({
    kind: "loading",
  } as never);

  mockedUseAnalysisResult.mockReturnValue({
    kind: "ready",
    refreshError: false,
    data: {
      lifecycle_status: "succeeded",
    },
  } as never);

  queueReport.mockReset();
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});

describe("Reports experience", () => {
  it("shows an honest loading state while report history is loading", () => {
    render(
      <ReportsClient
        workspaceId="workspace-1"
        projectId="project-1"
        runId="run-1"
      />,
    );

    expect(
      screen.getByText("Loading reports…"),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("No reports generated yet"),
    ).not.toBeInTheDocument();
  });

  it(
    "blocks duplicate generation while a report request is pending",
    async () => {
      mockedUseReports.mockReturnValue({
        kind: "ready",
        data: [],
      } as never);

      queueReport.mockImplementation(
        () =>
          new Promise(
            () => {
              // Keep the request pending so duplicate-submit
              // protection can be inspected.
            },
          ),
      );

      render(
        <ReportsClient
          workspaceId="workspace-1"
          projectId="project-1"
          runId="run-1"
        />,
      );

      const pdfButton = screen.getByRole(
        "button",
        {
          name: "Generate PDF",
        },
      );

      fireEvent.click(pdfButton);
      fireEvent.click(pdfButton);

      expect(
        queueReport,
      ).toHaveBeenCalledTimes(1);

      expect(
        pdfButton,
      ).toBeDisabled();

      expect(
        screen.getByText("Generating PDF…"),
      ).toBeInTheDocument();
    },
  );

  it(
    "refreshes backend report history after generation is queued",
    async () => {
      mockedUseReports.mockReturnValue({
        kind: "ready",
        data: [],
      } as never);

      queueReport.mockResolvedValue({
        id: "report-1",
        version: 1,
        format: "pdf",
        status: "pending",
        attempt_count: 0,
        max_attempts: 3,
        failure_reason: null,
        created_at: "2026-07-19T16:00:00Z",
      });

      render(
        <ReportsClient
          workspaceId="workspace-1"
          projectId="project-1"
          runId="run-1"
        />,
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Generate PDF",
          },
        ),
      );

      await waitFor(() => {
        expect(
          queueReport,
        ).toHaveBeenCalledTimes(1);
      });

      await waitFor(() => {
        expect(
          mockedUseReports,
        ).toHaveBeenLastCalledWith(
          "workspace-1",
          "project-1",
          "run-1",
          1,
        );
      });
    },
  );

  it.each([
    "queued",
    "running",
    "retrying",
  ])(
    "blocks report generation while the analysis is %s",
    (lifecycleStatus) => {
      mockedUseReports.mockReturnValue({
        kind: "ready",
        data: [],
      } as never);

      mockedUseAnalysisResult.mockReturnValue({
        kind: "ready",
        refreshError: false,
        data: {
          lifecycle_status:
            lifecycleStatus,
        },
      } as never);

      render(
        <ReportsClient
          workspaceId="workspace-1"
          projectId="project-1"
          runId="run-1"
        />,
      );

      expect(
        screen.queryByRole(
          "button",
          {
            name: "Generate PDF",
          },
        ),
      ).not.toBeInTheDocument();

      expect(
        screen.queryByRole(
          "button",
          {
            name: "Generate CSV",
          },
        ),
      ).not.toBeInTheDocument();

      expect(
        screen.getByText(
          "Reports will be available after this analysis completes.",
        ),
      ).toBeInTheDocument();

      expect(
        queueReport,
      ).not.toHaveBeenCalled();
    },
  );


  it(
    "regenerates a failed report using its existing format",
    async () => {
      mockedUseReports.mockReturnValue({
        kind: "ready",
        data: [
          {
            id: "failed-report-1",
            workspace_id: "workspace-1",
            project_id: "project-1",
            analysis_run_id: "run-1",
            version: 1,
            format: "pdf",
            status: "failed",
            attempt_count: 3,
            max_attempts: 3,
            failure_reason:
              "Report generation failed. Please regenerate the report.",
            created_at:
              "2026-07-19T16:00:00Z",
          },
        ],
      } as never);

      queueReport.mockResolvedValue({
        id: "report-2",
        version: 2,
        format: "pdf",
        status: "pending",
        attempt_count: 0,
        max_attempts: 3,
        failure_reason: null,
        created_at:
          "2026-07-19T16:05:00Z",
      });

      render(
        <ReportsClient
          workspaceId="workspace-1"
          projectId="project-1"
          runId="run-1"
        />,
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Regenerate PDF",
          },
        ),
      );

      await waitFor(() => {
        expect(
          queueReport,
        ).toHaveBeenCalledWith(
          "workspace-1",
          "project-1",
          "run-1",
          "pdf",
          "session-token",
        );
      });

      await waitFor(() => {
        expect(
          mockedUseReports,
        ).toHaveBeenLastCalledWith(
          "workspace-1",
          "project-1",
          "run-1",
          1,
        );
      });
    },
  );


  it(
    "links back to the exact results and reproducibility pages",
    () => {
      mockedUseReports.mockReturnValue({
        kind: "ready",
        data: [],
      } as never);

      render(
        <ReportsClient
          workspaceId="workspace-1"
          projectId="project-1"
          runId="run-1"
        />,
      );

      expect(
        screen.getByRole(
          "link",
          {
            name: "View Results",
          },
        ),
      ).toHaveAttribute(
        "href",
        "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1/result",
      );

      expect(
        screen.getByRole(
          "link",
          {
            name: "View Reproducibility",
          },
        ),
      ).toHaveAttribute(
        "href",
        "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1/lineage",
      );
    },
  );

});
