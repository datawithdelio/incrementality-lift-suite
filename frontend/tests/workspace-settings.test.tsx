import {
  cleanup,
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

import { WorkspaceSettings } from "@/components/settings/workspace-settings";
import { SESSION_TOKEN_KEY } from "@/lib/auth/api";
import {
  listWorkspaces,
} from "@/lib/workspaces/api";

vi.mock("@/lib/workspaces/api", () => ({
  listWorkspaces: vi.fn(),
}));

const mockedListWorkspaces =
  vi.mocked(listWorkspaces);

afterEach(() => {
  cleanup();
});

describe("Workspace Settings", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem(
      SESSION_TOKEN_KEY,
      "valid-token",
    );

    mockedListWorkspaces.mockReset();
  });

  it("renders the real scoped workspace information and current role", async () => {
    mockedListWorkspaces.mockResolvedValue([
      {
        workspace_id: "workspace-1",
        organization_id: "organization-1",
        name: "Northstar Measurement",
        slug: "northstar-measurement",
        role: "owner",
      },
      {
        workspace_id: "workspace-2",
        organization_id: "organization-2",
        name: "Other Workspace",
        slug: "other-workspace",
        role: "viewer",
      },
    ]);

    render(
      <WorkspaceSettings
        workspaceId="workspace-1"
      />,
    );

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Loading workspace settings",
    );

    expect(
      await screen.findByRole("heading", {
        name: "Workspace settings",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Northstar Measurement",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Owner"),
    ).toBeInTheDocument();

    expect(
      screen.queryByText(
        "Other Workspace",
      ),
    ).not.toBeInTheDocument();

    expect(
      mockedListWorkspaces,
    ).toHaveBeenCalledWith(
      "valid-token",
    );
  });

  it("does not expose unsupported workspace editing controls", async () => {
    mockedListWorkspaces.mockResolvedValue([
      {
        workspace_id: "workspace-1",
        organization_id: "organization-1",
        name: "Northstar Measurement",
        slug: "northstar-measurement",
        role: "admin",
      },
    ]);

    render(
      <WorkspaceSettings
        workspaceId="workspace-1"
      />,
    );

    await screen.findByRole("heading", {
      name: "Workspace settings",
    });

    expect(
      screen.queryByRole("button", {
        name: /edit workspace/i,
      }),
    ).not.toBeInTheDocument();

    expect(
      screen.queryByRole("button", {
        name: /save workspace/i,
      }),
    ).not.toBeInTheDocument();

    expect(
      screen.getByText(
        /workspace details are currently read-only/i,
      ),
    ).toBeInTheDocument();
  });

  it("handles an unavailable workspace without leaking other workspace data", async () => {
    mockedListWorkspaces.mockResolvedValue([
      {
        workspace_id: "workspace-2",
        organization_id: "organization-2",
        name: "Private Workspace",
        slug: "private-workspace",
        role: "owner",
      },
    ]);

    render(
      <WorkspaceSettings
        workspaceId="workspace-1"
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByRole("alert"),
      ).toHaveTextContent(
        "This workspace is unavailable or you no longer have access.",
      );
    });

    expect(
      screen.queryByText(
        "Private Workspace",
      ),
    ).not.toBeInTheDocument();
  });
});
