import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../src/components/navigation/app-shell";

const push = vi.fn();
let pathname = "/workspaces/workspace-1/results-dashboard";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push }),
}));

afterEach(() => {
  cleanup();
  push.mockReset();
  pathname = "/workspaces/workspace-1/results-dashboard";
});

describe("AppShell", () => {
  it("marks the current workspace destination and preserves workspace scope", () => {
    render(<AppShell workspaceId="workspace-1"><p>Dashboard content</p></AppShell>);

    expect(screen.getByRole("link", { name: /overview/i })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /channel performance/i })).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/channel-performance",
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
});
