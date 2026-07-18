import {
  cleanup,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { AuthPageGuard } from "../src/components/auth/auth-page-guard";

const replace = vi.fn();
const useAuth = vi.fn();

const router = {
  replace,
};

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

vi.mock("../src/components/auth/auth-provider", () => ({
  useAuth: () => useAuth(),
}));

afterEach(() => {
  cleanup();
  replace.mockReset();
  useAuth.mockReset();
});

describe("AuthPageGuard", () => {
  it("shows a stable loading state while session restoration is running", () => {
    useAuth.mockReturnValue({
      status: "checking",
      userId: null,
      establishSession: vi.fn(),
      signOut: vi.fn(),
    });

    render(
      <AuthPageGuard>
        <div data-testid="auth-form">
          Auth form
        </div>
      </AuthPageGuard>,
    );

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Checking your session",
    );

    expect(
      screen.queryByTestId("auth-form"),
    ).not.toBeInTheDocument();
  });

  it("renders auth content for unauthenticated users", () => {
    useAuth.mockReturnValue({
      status: "unauthenticated",
      userId: null,
      establishSession: vi.fn(),
      signOut: vi.fn(),
    });

    render(
      <AuthPageGuard>
        <div data-testid="auth-form">
          Auth form
        </div>
      </AuthPageGuard>,
    );

    expect(
      screen.getByTestId("auth-form"),
    ).toBeInTheDocument();

    expect(replace).not.toHaveBeenCalled();
  });

  it("redirects authenticated users away from auth pages", async () => {
    useAuth.mockReturnValue({
      status: "authenticated",
      userId: "user-1",
      establishSession: vi.fn(),
      signOut: vi.fn(),
    });

    render(
      <AuthPageGuard>
        <div data-testid="auth-form">
          Auth form
        </div>
      </AuthPageGuard>,
    );

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/"),
    );

    expect(
      screen.queryByTestId("auth-form"),
    ).not.toBeInTheDocument();
  });
});
