import {
  cleanup,
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
  MembersAccess,
} from "@/components/settings/members-access";
import {
  SESSION_TOKEN_KEY,
} from "@/lib/auth/api";
import {
  listWorkspaceMembers,
  listWorkspaces,
} from "@/lib/workspaces/api";

vi.mock("@/lib/workspaces/api", () => ({
  listWorkspaces: vi.fn(),
  listWorkspaceMembers: vi.fn(),
  WorkspaceApiError: class WorkspaceApiError extends Error {},
}));

const mockedListWorkspaces =
  vi.mocked(listWorkspaces);

const mockedListWorkspaceMembers =
  vi.mocked(listWorkspaceMembers);

function workspace(
  role: string,
) {
  return {
    workspace_id: "workspace-1",
    organization_id: "organization-1",
    name: "Measurement Team",
    slug: "measurement-team",
    role,
  };
}

const members = [
  {
    display_name: "Delio Rincon",
    email: "delio@example.com",
    role: "owner",
    joined_at: "2026-07-01T12:00:00Z",
  },
  {
    display_name: "Jane Analyst",
    email: "jane@example.com",
    role: "analyst",
    joined_at: "2026-07-02T12:00:00Z",
  },
];

afterEach(() => {
  cleanup();
});

describe("Members & Access", () => {
  beforeEach(() => {
    window.localStorage.clear();

    window.localStorage.setItem(
      SESSION_TOKEN_KEY,
      "valid-token",
    );

    mockedListWorkspaces.mockReset();
    mockedListWorkspaceMembers.mockReset();
  });

  it.each([
    "owner",
    "admin",
  ])(
    "renders the real workspace member list for %s",
    async (role) => {
      mockedListWorkspaces.mockResolvedValue([
        workspace(role),
      ]);

      mockedListWorkspaceMembers.mockResolvedValue(
        members,
      );

      render(
        <MembersAccess
          workspaceId="workspace-1"
        />,
      );

      expect(
        screen.getByRole("status"),
      ).toHaveTextContent(
        "Loading members and access",
      );

      expect(
        await screen.findByRole(
          "heading",
          {
            name: "Members & Access",
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByText(
          "Delio Rincon",
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByText(
          "delio@example.com",
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByText(
          "Jane Analyst",
        ),
      ).toBeInTheDocument();

      expect(
        mockedListWorkspaceMembers,
      ).toHaveBeenCalledWith(
        "valid-token",
        "workspace-1",
      );
    },
  );

  it.each([
    "analyst",
    "viewer",
  ])(
    "keeps member listing restricted for %s",
    async (role) => {
      mockedListWorkspaces.mockResolvedValue([
        workspace(role),
      ]);

      render(
        <MembersAccess
          workspaceId="workspace-1"
        />,
      );

      expect(
        await screen.findByRole(
          "heading",
          {
            name: "Members & Access",
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByText(
          /you do not have permission to view workspace members/i,
        ),
      ).toBeInTheDocument();

      expect(
        mockedListWorkspaceMembers,
      ).not.toHaveBeenCalled();
    },
  );

  it("does not expose unsupported invitation, role-change, or removal actions", async () => {
    mockedListWorkspaces.mockResolvedValue([
      workspace("owner"),
    ]);

    mockedListWorkspaceMembers.mockResolvedValue(
      members,
    );

    render(
      <MembersAccess
        workspaceId="workspace-1"
      />,
    );

    await screen.findByText(
      "Delio Rincon",
    );

    expect(
      screen.queryByRole(
        "button",
        {
          name: /invite/i,
        },
      ),
    ).not.toBeInTheDocument();

    expect(
      screen.queryByRole(
        "button",
        {
          name: /remove/i,
        },
      ),
    ).not.toBeInTheDocument();

    expect(
      screen.queryByRole(
        "combobox",
        {
          name: /role/i,
        },
      ),
    ).not.toBeInTheDocument();

    expect(
      screen.getByText(
        /member invitations, role changes, and member removal are not available yet/i,
      ),
    ).toBeInTheDocument();
  });

  it("does not retain members from the previous workspace scope", async () => {
    mockedListWorkspaces
      .mockResolvedValueOnce([
        workspace("owner"),
      ])
      .mockResolvedValueOnce([
        {
          ...workspace(
            "admin",
          ),
          workspace_id:
            "workspace-2",
          name:
            "Experimentation",
        },
      ]);

    mockedListWorkspaceMembers
      .mockResolvedValueOnce(
        members,
      )
      .mockResolvedValueOnce([
        {
          display_name:
            "Workspace Two Admin",
          email:
            "admin-two@example.com",
          role:
            "admin",
          joined_at:
            "2026-07-03T12:00:00Z",
        },
      ]);

    const {
      rerender,
    } = render(
      <MembersAccess
        workspaceId="workspace-1"
      />,
    );

    expect(
      await screen.findByText(
        "Delio Rincon",
      ),
    ).toBeInTheDocument();

    rerender(
      <MembersAccess
        workspaceId="workspace-2"
      />,
    );

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Loading members and access",
    );

    expect(
      screen.queryByText(
        "Delio Rincon",
      ),
    ).not.toBeInTheDocument();

    expect(
      await screen.findByText(
        "Workspace Two Admin",
      ),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        mockedListWorkspaceMembers,
      ).toHaveBeenLastCalledWith(
        "valid-token",
        "workspace-2",
      );
    });
  });

  it("fails safely when the active workspace is unavailable", async () => {
    mockedListWorkspaces.mockResolvedValue([
      {
        ...workspace(
          "owner",
        ),
        workspace_id:
          "other-workspace",
      },
    ]);

    render(
      <MembersAccess
        workspaceId="workspace-1"
      />,
    );

    expect(
      await screen.findByRole(
        "alert",
      ),
    ).toHaveTextContent(
      /members and access are unavailable/i,
    );

    expect(
      mockedListWorkspaceMembers,
    ).not.toHaveBeenCalled();
  });
});
