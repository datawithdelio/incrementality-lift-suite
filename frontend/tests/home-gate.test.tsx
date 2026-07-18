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

import { HomeGate } from "../src/components/home/home-gate";

const useAuth = vi.fn();

vi.mock("../src/components/auth/auth-provider", () => ({
  useAuth: () => useAuth(),
}));

vi.mock("../src/components/workspaces/workspace-bootstrap", () => ({
  WorkspaceBootstrap: () => (
    <div data-testid="workspace-bootstrap">
      Workspace bootstrap
    </div>
  ),
}));

afterEach(() => {
  cleanup();
  useAuth.mockReset();
});

describe("HomeGate", () => {
  it("shows a stable loading state while authentication is being checked", () => {
    useAuth.mockReturnValue({
      status: "checking",
      userId: null,
      establishSession: vi.fn(),
      signOut: vi.fn(),
    });

    render(
      <HomeGate>
        <div data-testid="public-landing">
          Public landing
        </div>
      </HomeGate>,
    );

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Checking your session",
    );

    expect(
      screen.queryByTestId("public-landing"),
    ).not.toBeInTheDocument();

    expect(
      screen.queryByTestId("workspace-bootstrap"),
    ).not.toBeInTheDocument();
  });

  it("shows the public landing page to unauthenticated visitors", () => {
    useAuth.mockReturnValue({
      status: "unauthenticated",
      userId: null,
      establishSession: vi.fn(),
      signOut: vi.fn(),
    });

    render(
      <HomeGate>
        <div data-testid="public-landing">
          Public landing
        </div>
      </HomeGate>,
    );

    expect(
      screen.getByTestId("public-landing"),
    ).toBeInTheDocument();

    expect(
      screen.queryByTestId("workspace-bootstrap"),
    ).not.toBeInTheDocument();
  });

  it("starts workspace bootstrap for authenticated users", () => {
    useAuth.mockReturnValue({
      status: "authenticated",
      userId: "user-1",
      establishSession: vi.fn(),
      signOut: vi.fn(),
    });

    render(
      <HomeGate>
        <div data-testid="public-landing">
          Public landing
        </div>
      </HomeGate>,
    );

    expect(
      screen.getByTestId("workspace-bootstrap"),
    ).toBeInTheDocument();

    expect(
      screen.queryByTestId("public-landing"),
    ).not.toBeInTheDocument();
  });
});
