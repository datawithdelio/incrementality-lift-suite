import {
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const {
  useAnalysisResultMock,
} = vi.hoisted(() => ({
  useAnalysisResultMock: vi.fn(),
}));

vi.mock(
  "../src/lib/results/use-analysis-result",
  () => ({
    useAnalysisResult:
      useAnalysisResultMock,
  }),
);

vi.mock(
  "../src/components/results/results-experience",
  () => ({
    ResultsExperience: ({
      onRetry,
    }: {
      onRetry?: () => void;
    }) => (
      <button
        type="button"
        onClick={onRetry}
      >
        Retry result
      </button>
    ),
  }),
);

import {
  ResultsPageClient,
} from "../src/components/results/results-page-client";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe(
  "ResultsPageClient retry",
  () => {
    it(
      "requests the same scoped result again when Retry is selected",
      () => {
        useAnalysisResultMock.mockReturnValue({
          kind: "loading",
        });

        render(
          <ResultsPageClient
            workspaceId="workspace-1"
            projectId="project-1"
            analysisRunId="run-1"
          />,
        );

        expect(
          useAnalysisResultMock,
        ).toHaveBeenLastCalledWith(
          "workspace-1",
          "project-1",
          "run-1",
          0,
        );

        fireEvent.click(
          screen.getByRole(
            "button",
            {
              name: "Retry result",
            },
          ),
        );

        expect(
          useAnalysisResultMock,
        ).toHaveBeenLastCalledWith(
          "workspace-1",
          "project-1",
          "run-1",
          1,
        );
      },
    );
  },
);
