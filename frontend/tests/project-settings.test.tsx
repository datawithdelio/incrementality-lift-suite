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

import { ProjectSettings } from "@/components/settings/project-settings";
import { SESSION_TOKEN_KEY } from "@/lib/auth/api";
import {
  getProject,
  updateProject,
} from "@/lib/projects/api";
import {
  listWorkspaces,
} from "@/lib/workspaces/api";

vi.mock("@/lib/projects/api", () => ({
  getProject: vi.fn(),
  updateProject: vi.fn(),
}));

vi.mock("@/lib/workspaces/api", () => ({
  listWorkspaces: vi.fn(),
}));

const mockedGetProject =
  vi.mocked(getProject);

const mockedUpdateProject =
  vi.mocked(updateProject);

const mockedListWorkspaces =
  vi.mocked(listWorkspaces);

const project = {
  id: "project-1",
  workspace_id: "workspace-1",
  created_by_user_id: "user-1",
  name: "Paid Search Lift",
  slug: "paid-search-lift",
  description: "Measure incremental conversions.",
  status: "active" as const,
  created_at: "2026-07-01T12:00:00Z",
  archived_at: null,
};

function workspace(
  role: string,
) {
  return {
    workspace_id: "workspace-1",
    organization_id: "organization-1",
    name: "Northstar Measurement",
    slug: "northstar-measurement",
    role,
  };
}

afterEach(() => {
  cleanup();
});

describe("Project Settings", () => {
  beforeEach(() => {
    window.localStorage.clear();

    window.localStorage.setItem(
      SESSION_TOKEN_KEY,
      "valid-token",
    );

    mockedGetProject.mockReset();
    mockedUpdateProject.mockReset();
    mockedListWorkspaces.mockReset();
  });

  it("renders the correct scoped project information", async () => {
    mockedGetProject.mockResolvedValue(
      project,
    );

    mockedListWorkspaces.mockResolvedValue([
      workspace("owner"),
    ]);

    render(
      <ProjectSettings
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Loading project settings",
    );

    expect(
      await screen.findByRole(
        "heading",
        {
          name: "Project settings",
        },
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Paid Search Lift",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Measure incremental conversions.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "paid-search-lift",
      ),
    ).toBeInTheDocument();

    expect(
      mockedGetProject,
    ).toHaveBeenCalledWith(
      "valid-token",
      "workspace-1",
      "project-1",
    );
  });

  it.each([
    "owner",
    "admin",
    "analyst",
  ])(
    "allows %s to update supported project fields",
    async (role) => {
      mockedGetProject.mockResolvedValue(
        project,
      );

      mockedListWorkspaces.mockResolvedValue([
        workspace(role),
      ]);

      mockedUpdateProject.mockResolvedValue({
        ...project,
        name: "Updated Lift Study",
        description: "Updated project scope.",
      });

      render(
        <ProjectSettings
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      await screen.findByRole(
        "heading",
        {
          name: "Project settings",
        },
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Edit project",
          },
        ),
      );

      fireEvent.change(
        screen.getByLabelText(
          "Project name",
        ),
        {
          target: {
            value:
              "  Updated Lift Study  ",
          },
        },
      );

      fireEvent.change(
        screen.getByLabelText(
          "Description",
        ),
        {
          target: {
            value:
              "  Updated project scope.  ",
          },
        },
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Save changes",
          },
        ),
      );

      await waitFor(() => {
        expect(
          mockedUpdateProject,
        ).toHaveBeenCalledWith(
          "valid-token",
          "workspace-1",
          "project-1",
          {
            name:
              "Updated Lift Study",
            description:
              "Updated project scope.",
          },
        );
      });

      expect(
        await screen.findByText(
          "Updated Lift Study",
        ),
      ).toBeInTheDocument();
    },
  );

  it("keeps viewers read-only", async () => {
    mockedGetProject.mockResolvedValue(
      project,
    );

    mockedListWorkspaces.mockResolvedValue([
      workspace("viewer"),
    ]);

    render(
      <ProjectSettings
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    await screen.findByRole(
      "heading",
      {
        name: "Project settings",
      },
    );

    expect(
      screen.queryByRole(
        "button",
        {
          name: "Edit project",
        },
      ),
    ).not.toBeInTheDocument();

    expect(
      screen.getByText(
        /you have read-only access to project settings/i,
      ),
    ).toBeInTheDocument();
  });

  it("does not retain Project A data when the project scope changes", async () => {
    mockedListWorkspaces.mockResolvedValue([
      workspace("owner"),
    ]);

    mockedGetProject
      .mockResolvedValueOnce(
        project,
      )
      .mockResolvedValueOnce({
        ...project,
        id: "project-2",
        name: "Geo Holdout",
        slug: "geo-holdout",
        description:
          "Measure regional lift.",
      });

    const {
      rerender,
    } = render(
      <ProjectSettings
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText(
        "Paid Search Lift",
      ),
    ).toBeInTheDocument();

    rerender(
      <ProjectSettings
        workspaceId="workspace-1"
        projectId="project-2"
      />,
    );

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Loading project settings",
    );

    expect(
      screen.queryByText(
        "Paid Search Lift",
      ),
    ).not.toBeInTheDocument();

    expect(
      await screen.findByText(
        "Geo Holdout",
      ),
    ).toBeInTheDocument();
  });
});
