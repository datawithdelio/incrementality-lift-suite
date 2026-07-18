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

import { WorkspaceSwitcher } from "../src/components/workspaces/workspace-switcher";

const push = vi.fn();
const listWorkspaces = vi.fn();

let pathname =
  "/workspaces/workspace-1/channel-performance";

const router = {
  push,
};

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => router,
}));

vi.mock("../src/lib/workspaces/api", () => ({
  listWorkspaces: (...args: unknown[]) =>
    listWorkspaces(...args),
}));

beforeEach(() => {
  localStorage.setItem(
    "incrementality_session_token",
    "session-token",
  );

  listWorkspaces.mockResolvedValue([
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
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  push.mockReset();
  listWorkspaces.mockReset();

  pathname =
    "/workspaces/workspace-1/channel-performance";
});

describe("WorkspaceSwitcher", () => {
  it("shows the real active workspace", async () => {
    render(
      <WorkspaceSwitcher
        workspaceId="workspace-1"
      />,
    );

    expect(
      await screen.findByRole(
        "button",
        { name: /Measurement Team/i },
      ),
    ).toBeInTheDocument();

    expect(
      listWorkspaces,
    ).toHaveBeenCalledWith(
      "session-token",
    );
  });

  it("switches workspace while preserving the current destination", async () => {
    render(
      <WorkspaceSwitcher
        workspaceId="workspace-1"
      />,
    );

    fireEvent.click(
      await screen.findByRole(
        "button",
        { name: /Measurement Team/i },
      ),
    );

    fireEvent.click(
      screen.getByRole(
        "menuitem",
        { name: /Experimentation/i },
      ),
    );

    expect(
      localStorage.getItem(
        "incrementality_workspace_id",
      ),
    ).toBe("workspace-2");

    expect(push).toHaveBeenCalledWith(
      "/workspaces/workspace-2/channel-performance",
    );
  });

  it("clears project context when switching workspaces", async () => {
    pathname = "/workspaces/workspace-1/projects/project-private";

    render(<WorkspaceSwitcher workspaceId="workspace-1" />);
    fireEvent.click(await screen.findByRole("button", { name: /Measurement Team/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Experimentation/i }));

    expect(push).toHaveBeenCalledWith("/workspaces/workspace-2");
  });

  it("falls back safely when workspace loading fails", async () => {
    listWorkspaces.mockRejectedValueOnce(
      new Error("network failure"),
    );

    render(
      <WorkspaceSwitcher
        workspaceId="workspace-1"
      />,
    );

    await waitFor(() =>
      expect(
        screen.getByRole(
          "button",
          { name: /Current workspace/i },
        ),
      ).toBeInTheDocument(),
    );

    expect(
      screen.queryByRole("alert"),
    ).not.toBeInTheDocument();
  });
});
