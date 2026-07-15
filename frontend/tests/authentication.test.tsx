import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthForm } from "../src/components/auth/auth-form";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
  push.mockReset();
});

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

describe("AuthForm", () => {
  it("logs in, stores the opaque session, and returns to the app", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({
      user_id: "user-1",
      session_token: "secret-session",
      token_type: "bearer",
      expires_at: "2026-07-21T12:00:00Z",
    }), { status: 200 }));

    render(<AuthForm mode="login" />);
    fireEvent.change(screen.getByLabelText("Work email"), { target: { value: "owner@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secure-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
    expect(localStorage.getItem("incrementality_session_token")).toBe("secret-session");
  });

  it("registers a workspace and signs the owner in automatically", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({
        organization_id: "org-1", workspace_id: "workspace-1",
        owner_user_id: "user-1", owner_membership_id: "membership-1",
      }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        user_id: "user-1", session_token: "registered-session",
        token_type: "bearer", expires_at: "2026-07-21T12:00:00Z",
      }), { status: 200 }));

    render(<AuthForm mode="register" />);
    fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "Avery Stone" } });
    fireEvent.change(screen.getByLabelText("Organization"), { target: { value: "Northstar Labs" } });
    fireEvent.change(screen.getByLabelText("Work email"), { target: { value: "avery@northstar.test" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "a-secure-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Create workspace" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/workspaces/workspace-1/results-dashboard"));
    expect(localStorage.getItem("incrementality_workspace_id")).toBe("workspace-1");
  });

  it("shows a safe message when credentials are rejected", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Invalid email or password." }), { status: 401 }));
    render(<AuthForm mode="login" />);
    fireEvent.change(screen.getByLabelText("Work email"), { target: { value: "owner@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
  });
});
