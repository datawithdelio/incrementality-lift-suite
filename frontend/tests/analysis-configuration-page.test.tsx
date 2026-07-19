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
  "../src/components/analysis-configuration/analysis-configuration-client",
  () => ({
    AnalysisConfigurationClient: ({
      workspaceId,
      projectId,
    }: {
      workspaceId: string;
      projectId: string;
    }) => (
      <div>
        Analysis Configuration Client:
        {workspaceId}/{projectId}
      </div>
    ),
  }),
);

import Page from "../src/app/workspaces/[workspaceId]/projects/[projectId]/analyses/new/page";

describe(
  "Analysis Configuration route",
  () => {
    it("restores workspace and project scope from direct URL params", async () => {
      const element = await Page({
        params: Promise.resolve({
          workspaceId: "workspace-1",
          projectId: "project-1",
        }),
      });

      render(element);

      expect(
        screen.getByText(
          "Analysis Configuration Client:workspace-1/project-1",
        ),
      ).toBeInTheDocument();
    });
  },
);
