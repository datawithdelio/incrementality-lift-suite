import {
  render,
  screen,
} from "@testing-library/react";
import {
  describe,
  expect,
  it,
  vi,
} from "vitest";

vi.mock(
  "../src/components/analysis-runs/analysis-run-status-page-client",
  () => ({
    AnalysisRunStatusPageClient: ({
      analysisRunId,
    }: {
      analysisRunId: string;
    }) => (
      <div>
        Status page {analysisRunId}
      </div>
    ),
  }),
);

vi.mock(
  "../src/components/results/results-page-client",
  () => ({
    ResultsPageClient: ({
      analysisRunId,
    }: {
      analysisRunId: string;
    }) => (
      <div>
        Results page {analysisRunId}
      </div>
    ),
  }),
);

import AnalysisRunPage from "../src/app/workspaces/[workspaceId]/projects/[projectId]/analysis-runs/[analysisRunId]/page";
import AnalysisResultPage from "../src/app/workspaces/[workspaceId]/projects/[projectId]/analysis-runs/[analysisRunId]/result/page";

describe(
  "analysis run routes",
  () => {
    it(
      "renders execution status on the base run route",
      async () => {
        render(
          await AnalysisRunPage({
            params: Promise.resolve({
              workspaceId:
                "workspace-1",
              projectId:
                "project-1",
              analysisRunId:
                "run-1",
            }),
          }),
        );

        expect(
          screen.getByText(
            "Status page run-1",
          ),
        ).toBeInTheDocument();
      },
    );

    it(
      "renders full results on the dedicated result route",
      async () => {
        render(
          await AnalysisResultPage({
            params: Promise.resolve({
              workspaceId:
                "workspace-1",
              projectId:
                "project-1",
              analysisRunId:
                "run-1",
            }),
          }),
        );

        expect(
          screen.getByText(
            "Results page run-1",
          ),
        ).toBeInTheDocument();
      },
    );
  },
);
