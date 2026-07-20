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

import WorkspaceSettingsPage from "@/app/workspaces/[workspaceId]/settings/page";

vi.mock(
  "@/components/settings/workspace-settings",
  () => ({
    WorkspaceSettings: ({
      workspaceId,
    }: {
      workspaceId: string;
    }) => (
      <div>
        Workspace settings for {workspaceId}
      </div>
    ),
  }),
);

describe("Workspace Settings page", () => {
  it("preserves workspace scope from the route", async () => {
    const page = await WorkspaceSettingsPage({
      params: Promise.resolve({
        workspaceId: "workspace-1",
      }),
    });

    render(page);

    expect(
      screen.getByText(
        "Workspace settings for workspace-1",
      ),
    ).toBeInTheDocument();
  });
});
