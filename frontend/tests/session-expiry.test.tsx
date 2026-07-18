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

import {
  AuthProvider,
  useAuth,
} from "../src/components/auth/auth-provider";

function AuthStateProbe() {
  const auth = useAuth();

  return (
    <div>
      <span data-testid="auth-status">
        {auth.status}
      </span>

      {auth.sessionNotice && (
        <p role="alert">
          {auth.sessionNotice}
        </p>
      )}

      <button
        type="button"
        onClick={() =>
          auth.establishSession({
            user_id: "user-1",
            session_token: "fresh-session",
            token_type: "bearer",
            expires_at: "2026-07-21T12:00:00Z",
          })
        }
      >
        Establish fresh session
      </button>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.unstubAllGlobals();
});

describe("expired session UX", () => {
  it("does not show an expiry notice to a normal signed-out visitor", async () => {
    render(
      <AuthProvider>
        <AuthStateProbe />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("auth-status"),
      ).toHaveTextContent(
        "unauthenticated",
      ),
    );

    expect(
      screen.queryByRole("alert"),
    ).not.toBeInTheDocument();
  });

  it("remembers when a stored session is no longer valid", async () => {
    localStorage.setItem(
      "incrementality_session_token",
      "expired-session",
    );

    localStorage.setItem(
      "incrementality_workspace_id",
      "workspace-1",
    );

    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail:
            "Invalid or expired session.",
        }),
        { status: 401 },
      ),
    );

    render(
      <AuthProvider>
        <AuthStateProbe />
      </AuthProvider>,
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Your session expired",
    );

    expect(
      screen.getByTestId("auth-status"),
    ).toHaveTextContent(
      "unauthenticated",
    );

    expect(
      localStorage.getItem(
        "incrementality_session_token",
      ),
    ).toBeNull();

    expect(
      localStorage.getItem(
        "incrementality_workspace_id",
      ),
    ).toBeNull();
  });

  it("clears the expiry notice after a fresh session is established", async () => {
    localStorage.setItem(
      "incrementality_session_token",
      "expired-session",
    );

    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail:
            "Invalid or expired session.",
        }),
        { status: 401 },
      ),
    );

    render(
      <AuthProvider>
        <AuthStateProbe />
      </AuthProvider>,
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Your session expired",
    );

    fireEvent.click(
      screen.getByRole(
        "button",
        {
          name:
            "Establish fresh session",
        },
      ),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("auth-status"),
      ).toHaveTextContent(
        "authenticated",
      ),
    );

    expect(
      screen.queryByRole("alert"),
    ).not.toBeInTheDocument();

    expect(
      localStorage.getItem(
        "incrementality_session_token",
      ),
    ).toBe(
      "fresh-session",
    );
  });
});
