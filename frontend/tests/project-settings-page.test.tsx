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

import ProjectSettingsPage from "@/app/workspaces/[workspaceId]/projects/[projectId]/settings/page";

vi.mock(
  "@/components/settings/project-settings",
  () => ({
    ProjectSettings: ({
      workspaceId,
      projectId,
    }: {
      workspaceId: string;
      projectId: string;
    }) => (
      <div>
        Project settings for {workspaceId} / {projectId}
      </div>
    ),
  }),
);

describe("Project Settings page", () => {
  it("preserves workspace and project scope from the route", async () => {
    const page = await ProjectSettingsPage({
      params: Promise.resolve({
        workspaceId: "workspace-1",
        projectId: "project-1",
      }),
    });

    render(page);

    expect(
      screen.getByText(
        "Project settings for workspace-1 / project-1",
      ),
    ).toBeInTheDocument();
  });
});
