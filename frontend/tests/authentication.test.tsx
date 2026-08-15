import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RootLayout from "../src/app/layout";
import WorkspaceLayout from "../src/app/workspaces/[workspaceId]/layout";
import { AuthForm } from "../src/components/auth/auth-form";
import {
  AuthProvider,
  useAuth,
} from "../src/components/auth/auth-provider";
import { ProtectedRoute } from "../src/components/auth/protected-route";
import { AppToaster } from "../src/components/ui/app-toaster";
import {
  register,
  validateSession,
} from "../src/lib/auth/api";

const push = vi.fn();
const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
  push.mockReset();
  replace.mockReset();
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

    render(
      <AuthProvider>
        <AuthForm mode="login" />
      </AuthProvider>,
    );
    fireEvent.change(screen.getByLabelText("Work email"), { target: { value: "owner@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secure-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
    expect(localStorage.getItem("incrementality_session_token")).toBe("secret-session");
  });

  it("registers an account without creating a workspace and signs the user in", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user_id: "user-1",
          }),
          { status: 201 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user_id: "user-1",
            session_token: "registered-session",
            token_type: "bearer",
            expires_at: "2026-07-21T12:00:00Z",
          }),
          { status: 200 },
        ),
      );

    render(
      <AuthProvider>
        <AuthForm mode="register" />
      </AuthProvider>,
    );

    expect(
      screen.queryByLabelText("Organization"),
    ).not.toBeInTheDocument();

    fireEvent.change(
      screen.getByLabelText("Your name"),
      { target: { value: "Avery Stone" } },
    );

    fireEvent.change(
      screen.getByLabelText("Work email"),
      { target: { value: "avery@northstar.test" } },
    );

    fireEvent.change(
      screen.getByLabelText("Password"),
      { target: { value: "a-secure-password" } },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Create account" }),
    );

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/"),
    );

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/auth/register",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "avery@northstar.test",
          display_name: "Avery Stone",
          password: "a-secure-password",
        }),
      }),
    );

    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/auth/login",
      expect.objectContaining({
        method: "POST",
      }),
    );

    expect(
      localStorage.getItem("incrementality_session_token"),
    ).toBe("registered-session");

    expect(
      localStorage.getItem("incrementality_workspace_id"),
    ).toBeNull();
  });

  it("shows an actionable existing-email message during registration", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: "An account with this information already exists.",
        }),
        { status: 409 },
      ),
    );

    render(
      <AuthProvider>
        <AuthForm mode="register" />
      </AuthProvider>,
    );

    fireEvent.change(
      screen.getByLabelText("Your name"),
      { target: { value: "Avery Stone" } },
    );
    fireEvent.change(
      screen.getByLabelText("Work email"),
      { target: { value: "owner@example.com" } },
    );
    fireEvent.change(
      screen.getByLabelText("Password"),
      { target: { value: "a-secure-password" } },
    );
    fireEvent.click(
      screen.getByRole(
        "button",
        { name: "Create account" },
      ),
    );

    const alert = await screen.findByRole("alert");

    expect(alert).toHaveTextContent(
      "Email already registeredAn account with this email already exists.",
    );
    expect(
      screen.getByRole("link", { name: "Sign in instead" }),
    ).toHaveAttribute("href", "/login");
    expect(
      screen.getByLabelText("Work email"),
    ).toHaveAttribute("aria-invalid", "true");
  });

  it("shows a safe message when credentials are rejected", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Invalid email or password." }), { status: 401 }));
    render(
      <AuthProvider>
        <AuthForm mode="login" />
      </AuthProvider>,
    );
    fireEvent.change(screen.getByLabelText("Work email"), { target: { value: "owner@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
  });


  it("shows a safe network message when login cannot reach the API", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(
      new TypeError("Failed to fetch"),
    );

    render(
      <AuthProvider>
        <AuthForm mode="login" />
      </AuthProvider>,
    );

    fireEvent.change(
      screen.getByLabelText("Work email"),
      { target: { value: "owner@example.com" } },
    );

    fireEvent.change(
      screen.getByLabelText("Password"),
      { target: { value: "secure-password" } },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Sign in" }),
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "We couldn't reach the server. Please check your connection and try again.",
    );
  });

  it("prevents a second login submission while the first is pending", async () => {
    vi.mocked(fetch).mockImplementationOnce(
      () => new Promise<Response>(() => undefined),
    );

    render(
      <AuthProvider>
        <AuthForm mode="login" />
      </AuthProvider>,
    );

    fireEvent.change(
      screen.getByLabelText("Work email"),
      { target: { value: "owner@example.com" } },
    );

    fireEvent.change(
      screen.getByLabelText("Password"),
      { target: { value: "secure-password" } },
    );

    const submit = screen.getByRole(
      "button",
      { name: "Sign in" },
    );

    fireEvent.click(submit);

    await waitFor(() =>
      expect(submit).toBeDisabled(),
    );

    expect(fetch).toHaveBeenCalledTimes(1);

    fireEvent.click(submit);

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("explains when the demo server is still starting", async () => {
    vi.useFakeTimers();
    vi.mocked(fetch).mockImplementationOnce(
      () => new Promise<Response>(() => undefined),
    );

    render(
      <AuthProvider>
        <AuthForm mode="login" />
      </AuthProvider>,
    );

    fireEvent.change(screen.getByLabelText("Work email"), {
      target: { value: "owner@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secure-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await act(async () => {
      vi.advanceTimersByTime(6_000);
    });

    expect(screen.getByRole("status")).toHaveTextContent(
      "Starting the secure demo server",
    );
    vi.useRealTimers();
  });


  it("updates centralized authentication state after successful login", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          user_id: "user-1",
          session_token: "new-session",
          token_type: "bearer",
          expires_at: "2026-07-21T12:00:00Z",
        }),
        { status: 200 },
      ),
    );

    render(
      <AuthProvider>
        <AuthForm mode="login" />
        <AuthStateProbe />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("auth-status"),
      ).toHaveTextContent("unauthenticated"),
    );

    fireEvent.change(
      screen.getByLabelText("Work email"),
      { target: { value: "owner@example.com" } },
    );

    fireEvent.change(
      screen.getByLabelText("Password"),
      { target: { value: "secure-password" } },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Sign in" }),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("auth-status"),
      ).toHaveTextContent("authenticated"),
    );

    expect(
      screen.getByTestId("auth-user"),
    ).toHaveTextContent("user-1");

    expect(
      localStorage.getItem("incrementality_session_token"),
    ).toBe("new-session");
  });

});

describe("registration API", () => {
  it("translates a registration conflict into a specific email message", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: "An account with this information already exists.",
        }),
        { status: 409 },
      ),
    );

    await expect(
      register({
        displayName: "Avery Stone",
        email: "owner@example.com",
        password: "a-secure-password",
      }),
    ).rejects.toThrow(
      "An account with this email already exists.",
    );
  });
});

describe("session API", () => {
  it("validates a stored bearer session before restoring authentication", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          session_id: "session-1",
          user_id: "user-1",
          expires_at: "2026-07-21T12:00:00Z",
        }),
        { status: 200 },
      ),
    );

    const session = await validateSession("existing-session");

    expect(session).toEqual({
      session_id: "session-1",
      user_id: "user-1",
      expires_at: "2026-07-21T12:00:00Z",
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/auth/session",
      expect.objectContaining({
        method: "GET",
        headers: {
          Authorization: "Bearer existing-session",
        },
        cache: "no-store",
        signal: expect.any(AbortSignal),
      }),
    );
  });
});
function AuthStateProbe() {
  const auth = useAuth();

  return (
    <div>
      <span data-testid="auth-status">{auth.status}</span>
      {auth.userId && <span data-testid="auth-user">{auth.userId}</span>}
      <button type="button" onClick={() => void auth.signOut()}>
        Test sign out
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  it("checks a stored session before restoring authenticated state", async () => {
    localStorage.setItem("incrementality_session_token", "existing-session");

    let resolveSession!: (response: Response) => void;

    vi.mocked(fetch).mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          resolveSession = resolve;
        }),
    );

    render(
      <AuthProvider>
        <AuthStateProbe />
      </AuthProvider>,
    );

    expect(screen.getByTestId("auth-status")).toHaveTextContent("checking");
    expect(screen.queryByTestId("auth-user")).not.toBeInTheDocument();

    resolveSession(
      new Response(
        JSON.stringify({
          session_id: "session-1",
          user_id: "user-1",
          expires_at: "2026-07-21T12:00:00Z",
        }),
        { status: 200 },
      ),
    );

    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "authenticated",
      ),
    );

    expect(screen.getByTestId("auth-user")).toHaveTextContent("user-1");
  });


  it("clears an invalid stored session and becomes unauthenticated", async () => {
    localStorage.setItem("incrementality_session_token", "expired-session");
    localStorage.setItem(
      "incrementality_session_expires_at",
      "2026-07-01T12:00:00Z",
    );
    localStorage.setItem(
      "incrementality_workspace_id",
      "stale-workspace",
    );

    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: "Invalid or expired session.",
        }),
        { status: 401 },
      ),
    );

    render(
      <AuthProvider>
        <AuthStateProbe />
      </AuthProvider>,
    );

    expect(screen.getByTestId("auth-status")).toHaveTextContent("checking");

    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "unauthenticated",
      ),
    );

    expect(
      localStorage.getItem("incrementality_session_token"),
    ).toBeNull();

    expect(
      localStorage.getItem("incrementality_session_expires_at"),
    ).toBeNull();

    expect(
      localStorage.getItem("incrementality_workspace_id"),
    ).toBeNull();
  });



  it("signs out centrally, clears user-specific state, and becomes unauthenticated", async () => {
    localStorage.setItem(
      "incrementality_session_token",
      "active-session",
    );
    localStorage.setItem(
      "incrementality_session_expires_at",
      "2026-07-21T12:00:00Z",
    );
    localStorage.setItem(
      "incrementality_workspace_id",
      "workspace-1",
    );

    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            session_id: "session-1",
            user_id: "user-1",
            expires_at: "2026-07-21T12:00:00Z",
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(null, { status: 204 }),
      );

    render(
      <AuthProvider>
        <AuthStateProbe />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "authenticated",
      ),
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Test sign out" }),
    );

    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "unauthenticated",
      ),
    );

    expect(
      localStorage.getItem("incrementality_session_token"),
    ).toBeNull();

    expect(
      localStorage.getItem("incrementality_session_expires_at"),
    ).toBeNull();

    expect(
      localStorage.getItem("incrementality_workspace_id"),
    ).toBeNull();

    expect(fetch).toHaveBeenLastCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({
        method: "POST",
        headers: {
          Authorization: "Bearer active-session",
        },
        signal: expect.any(AbortSignal),
      }),
    );
  });

});
describe("ProtectedRoute", () => {
  it("does not expose protected content while authentication is being resolved", () => {
    localStorage.setItem(
      "incrementality_session_token",
      "existing-session",
    );

    vi.mocked(fetch).mockImplementationOnce(
      () => new Promise<Response>(() => undefined),
    );

    render(
      <AuthProvider>
        <ProtectedRoute>
          <p>Private dashboard</p>
        </ProtectedRoute>
      </AuthProvider>,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Checking your session",
    );

    expect(
      screen.queryByText("Private dashboard"),
    ).not.toBeInTheDocument();

    expect(replace).not.toHaveBeenCalled();
  });

  it("redirects an unauthenticated user without exposing protected content", async () => {
    render(
      <AuthProvider>
        <ProtectedRoute>
          <p>Private dashboard</p>
        </ProtectedRoute>
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/login"),
    );

    expect(
      screen.queryByText("Private dashboard"),
    ).not.toBeInTheDocument();
  });
});
describe("application auth integration", () => {
  it("wires authentication and global feedback at the application root", () => {
    const element = RootLayout({
      children: <p>Application content</p>,
    });

    const body = element.props.children;

    expect(body.type).toBe("body");
    expect(body.props.children.type).toBe(AuthProvider);
    expect(body.props.children.props.children[1].type).toBe(AppToaster);
  });

  it("wires protected workspace routes through ProtectedRoute", async () => {
    const element = await WorkspaceLayout({
      children: <p>Private workspace content</p>,
      params: Promise.resolve({
        workspaceId: "workspace-1",
      }),
    });

    expect(element.type).toBe(ProtectedRoute);
  });
});
