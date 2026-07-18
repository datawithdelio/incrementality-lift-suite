import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../src/components/navigation/app-shell";

const push = vi.fn();
const authSignOut = vi.fn();
let pathname = "/workspaces/workspace-1/results-dashboard";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push }),
}));

vi.mock("../src/components/auth/auth-provider", () => ({
  useAuth: () => ({
    status: "authenticated",
    userId: "user-1",
    signOut: authSignOut,
  }),
}));

afterEach(() => {
  cleanup();
  push.mockReset();
  authSignOut.mockReset();
  pathname = "/workspaces/workspace-1/results-dashboard";
});

describe("AppShell", () => {
  it("marks the current workspace destination and preserves workspace scope", () => {
    render(<AppShell workspaceId="workspace-1"><p>Dashboard content</p></AppShell>);

    expect(screen.getByRole("link", { name: /^measurement$/i })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /projects/i })).toHaveAttribute(
      "href",
      "/workspaces/workspace-1",
    );
    expect(screen.getByRole("link", { name: /channel performance/i })).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/channel-performance",
    );
  });

  it("adds a canonical project overview destination in project context", () => {
    pathname = "/workspaces/workspace-1/projects/project-1";
    render(<AppShell workspaceId="workspace-1"><p>Project content</p></AppShell>);

    expect(screen.getByRole("link", { name: /project overview/i })).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1",
    );
    expect(screen.getByRole("link", { name: /project overview/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("opens searchable navigation with the keyboard and filters destinations", async () => {
    render(<AppShell workspaceId="workspace-1"><p>Dashboard content</p></AppShell>);

    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const search = screen.getByRole("combobox", { name: "Search workspace" });
    await waitFor(() => expect(search).toHaveFocus());

    fireEvent.change(search, { target: { value: "channel" } });
    expect(screen.getByRole("option", { name: /channel performance/i })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /overview/i })).not.toBeInTheDocument();
  });

  it("closes the command palette with Escape", () => {
    render(<AppShell workspaceId="workspace-1"><p>Dashboard content</p></AppShell>);
    fireEvent.click(screen.getByRole("button", { name: /search workspace/i }));
    expect(screen.getByRole("dialog", { name: "Search workspace" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Search workspace" })).not.toBeInTheDocument();
  });

  it("supports fast keyboard navigation without requiring a pointer", async () => {
    render(<AppShell workspaceId="workspace-1"><p>Dashboard content</p></AppShell>);

    fireEvent.click(screen.getByRole("button", { name: /search workspace/i }));
    const search = screen.getByRole("combobox", { name: "Search workspace" });
    await waitFor(() => expect(search).toHaveFocus());

    fireEvent.keyDown(search, { key: "ArrowDown" });
    fireEvent.keyDown(search, { key: "ArrowDown" });
    expect(screen.getByRole("option", { name: /channel performance/i })).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(search, { key: "Enter" });

    expect(push).toHaveBeenCalledWith("/workspaces/workspace-1/channel-performance");
  });


  it("delegates sign out to the centralized authentication boundary", async () => {
    authSignOut.mockResolvedValueOnce(undefined);

    render(
      <AppShell workspaceId="workspace-1">
        <p>Dashboard content</p>
      </AppShell>,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /sign out/i }),
    );

    await waitFor(() =>
      expect(authSignOut).toHaveBeenCalledTimes(1),
    );
  });

});
