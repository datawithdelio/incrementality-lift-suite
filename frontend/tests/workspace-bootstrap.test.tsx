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

import { WorkspaceBootstrap } from "../src/components/workspaces/workspace-bootstrap";

const push = vi.fn();
const listWorkspaces = vi.fn();
const createWorkspace = vi.fn();

const router = {
  push,
};

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

vi.mock("../src/components/auth/auth-provider", () => ({
  useAuth: () => ({
    status: "authenticated",
    userId: "user-1",
    establishSession: vi.fn(),
    signOut: vi.fn(),
  }),
}));

vi.mock("../src/lib/workspaces/api", () => ({
  listWorkspaces: (...args: unknown[]) =>
    listWorkspaces(...args),
  createWorkspace: (...args: unknown[]) =>
    createWorkspace(...args),
}));

beforeEach(() => {
  localStorage.setItem(
    "incrementality_session_token",
    "session-token",
  );
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  push.mockReset();
  listWorkspaces.mockReset();
  createWorkspace.mockReset();
});

describe("WorkspaceBootstrap", () => {
  it("shows first-workspace onboarding when the user has no workspaces", async () => {
    listWorkspaces.mockResolvedValueOnce([]);

    render(<WorkspaceBootstrap />);

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Loading your workspace",
    );

    expect(
      await screen.findByRole(
        "heading",
        { name: "Create your first workspace" },
      ),
    ).toBeInTheDocument();

    expect(push).not.toHaveBeenCalled();
  });

  it("activates and enters the only accessible workspace", async () => {
    listWorkspaces.mockResolvedValueOnce([
      {
        workspace_id: "workspace-1",
        organization_id: "organization-1",
        name: "Measurement Team",
        slug: "measurement-team",
        role: "owner",
      },
    ]);

    render(<WorkspaceBootstrap />);

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        "/workspaces/workspace-1/results-dashboard",
      ),
    );

    expect(
      localStorage.getItem(
        "incrementality_workspace_id",
      ),
    ).toBe("workspace-1");
  });

  it("creates the first workspace and enters it", async () => {
    listWorkspaces.mockResolvedValueOnce([]);

    createWorkspace.mockResolvedValueOnce({
      organization_id: "organization-1",
      workspace_id: "workspace-new",
      membership_id: "membership-1",
    });

    render(<WorkspaceBootstrap />);

    await screen.findByRole(
      "heading",
      { name: "Create your first workspace" },
    );

    fireEvent.change(
      screen.getByLabelText("Organization"),
      { target: { value: "Northstar Labs" } },
    );

    fireEvent.change(
      screen.getByLabelText("Workspace name"),
      { target: { value: "Measurement Team" } },
    );

    fireEvent.click(
      screen.getByRole(
        "button",
        { name: "Create workspace" },
      ),
    );

    await waitFor(() =>
      expect(createWorkspace).toHaveBeenCalledWith(
        "session-token",
        {
          organizationName: "Northstar Labs",
          workspaceName: "Measurement Team",
        },
      ),
    );

    expect(
      localStorage.getItem(
        "incrementality_workspace_id",
      ),
    ).toBe("workspace-new");

    expect(push).toHaveBeenCalledWith(
      "/workspaces/workspace-new/results-dashboard",
    );
  });

  it("lets a user choose between multiple accessible workspaces", async () => {
    listWorkspaces.mockResolvedValueOnce([
      {
        workspace_id: "workspace-1",
        organization_id: "organization-1",
        name: "Measurement Team",
        slug: "measurement-team",
        role: "owner",
      },
      {
        workspace_id: "workspace-2",
        organization_id: "organization-2",
        name: "Experimentation",
        slug: "experimentation",
        role: "analyst",
      },
    ]);

    render(<WorkspaceBootstrap />);

    expect(
      await screen.findByRole(
        "heading",
        { name: "Choose a workspace" },
      ),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole(
        "button",
        { name: /Experimentation/i },
      ),
    );

    expect(
      localStorage.getItem(
        "incrementality_workspace_id",
      ),
    ).toBe("workspace-2");

    expect(push).toHaveBeenCalledWith(
      "/workspaces/workspace-2/results-dashboard",
    );
  });

  it("shows a recoverable error and retries workspace loading", async () => {
    listWorkspaces
      .mockRejectedValueOnce(
        new Error("network failure"),
      )
      .mockResolvedValueOnce([]);

    render(<WorkspaceBootstrap />);

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "We couldn't load your workspaces",
    );

    fireEvent.click(
      screen.getByRole(
        "button",
        { name: "Retry" },
      ),
    );

    expect(
      await screen.findByRole(
        "heading",
        { name: "Create your first workspace" },
      ),
    ).toBeInTheDocument();

    expect(
      listWorkspaces,
    ).toHaveBeenCalledTimes(2);
  });

});
