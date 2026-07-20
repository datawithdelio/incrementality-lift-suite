import { describe, expect, it } from "vitest";

import {
  projectSettingsPath,
  workspaceMembersPath,
  workspaceSettingsPath,
} from "@/lib/projects/routes";

describe("settings route helpers", () => {
  it("builds the workspace settings route", () => {
    expect(
      workspaceSettingsPath("workspace-1"),
    ).toBe(
      "/workspaces/workspace-1/settings",
    );
  });

  it("builds the workspace members and access route", () => {
    expect(
      workspaceMembersPath("workspace-1"),
    ).toBe(
      "/workspaces/workspace-1/members",
    );
  });

  it("builds the project settings route with workspace scope preserved", () => {
    expect(
      projectSettingsPath(
        "workspace-1",
        "project-1",
      ),
    ).toBe(
      "/workspaces/workspace-1/projects/project-1/settings",
    );
  });
});
