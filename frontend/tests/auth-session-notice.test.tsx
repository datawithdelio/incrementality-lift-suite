import {
  cleanup,
  render,
  screen,
} from "@testing-library/react";
import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { AuthForm } from "../src/components/auth/auth-form";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
  }),
}));

vi.mock("../src/components/auth/auth-provider", () => ({
  useAuth: () => ({
    status: "unauthenticated",
    userId: null,
    sessionNotice:
      "Your session expired. Please sign in again.",
    establishSession: vi.fn(),
    signOut: vi.fn(),
  }),
}));

afterEach(() => {
  cleanup();
  push.mockReset();
});

describe("AuthForm session notice", () => {
  it("shows an expired-session notice on the login form", () => {
    render(
      <AuthForm mode="login" />,
    );

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(
      "Your session expired. Please sign in again.",
    );
  });

  it("does not show the session notice on registration", () => {
    render(
      <AuthForm mode="register" />,
    );

    expect(
      screen.queryByText(
        "Your session expired. Please sign in again.",
      ),
    ).not.toBeInTheDocument();
  });
});
