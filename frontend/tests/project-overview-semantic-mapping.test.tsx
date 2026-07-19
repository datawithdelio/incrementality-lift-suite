import {
  cleanup,
  render,
  screen,
} from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { ProjectOverview } from "@/components/projects/project-overview";
import { SESSION_TOKEN_KEY } from "@/lib/auth/api";

const {
  getProjectOverviewMock,
  listProjectsMock,
  routerPushMock,
  updateProjectMock,
} = vi.hoisted(() => ({
  getProjectOverviewMock: vi.fn(),
  listProjectsMock: vi.fn(),
  routerPushMock: vi.fn(),
  updateProjectMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPushMock,
  }),
}));

vi.mock("@/lib/projects/api", () => ({
  ProjectApiError: class ProjectApiError extends Error {},
  getProjectOverview:
    getProjectOverviewMock,
  listProjects:
    listProjectsMock,
  updateProject:
    updateProjectMock,
}));

const baseProject = {
  id: "project-1",
  workspace_id: "workspace-1",
  created_by_user_id: "user-1",
  name: "Lift Study",
  slug: "lift-study",
  description: "Incrementality study",
  status: "active",
  created_at: "2026-07-18T12:00:00Z",
  archived_at: null,
  latest_dataset_id: "dataset-1",
  latest_dataset_status: "ready",
  latest_analysis_run_id: null,
  latest_analysis_run_status: null,
};

describe(
  "Project Overview semantic mapping integration",
  () => {
    beforeEach(() => {
      window.localStorage.setItem(
        SESSION_TOKEN_KEY,
        "session-token",
      );

      listProjectsMock.mockResolvedValue([
        baseProject,
      ]);
    });

    afterEach(() => {
      cleanup();
      window.localStorage.clear();
      vi.clearAllMocks();
    });

    it("routes the recommended next step to Mapping for a ready unmapped dataset", async () => {
      getProjectOverviewMock.mockResolvedValue({
        ...baseProject,
        semantic_mapping_configured: false,
      });

      render(
        <ProjectOverview
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      expect(
        await screen.findByRole(
          "heading",
          {
            name: "Map the dataset columns",
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByRole(
          "link",
          {
            name: /Open current step/i,
          },
        ),
      ).toHaveAttribute(
        "href",
        "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/mapping",
      );
    });

    it("exposes View/Edit Mapping for a ready dataset with an existing mapping", async () => {
      getProjectOverviewMock.mockResolvedValue({
        ...baseProject,
        semantic_mapping_configured: true,
      });

      render(
        <ProjectOverview
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      await screen.findByRole(
        "heading",
        {
          name: "Configure the first analysis",
        },
      );

      expect(
        screen.getByRole(
          "link",
          {
            name: /View\/Edit Mapping/i,
          },
        ),
      ).toHaveAttribute(
        "href",
        "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/mapping",
      );
    });
    it("routes the recommended next step to analysis configuration for a ready mapped dataset", async () => {
      getProjectOverviewMock.mockResolvedValue({
        ...baseProject,
        semantic_mapping_configured: true,
      });

      render(
        <ProjectOverview
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      expect(
        await screen.findByRole(
          "heading",
          {
            name: "Configure the first analysis",
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByRole(
          "link",
          {
            name: /Open current step/i,
          },
        ),
      ).toHaveAttribute(
        "href",
        "/workspaces/workspace-1/projects/project-1/analyses/new",
      );
    });

  },
);
