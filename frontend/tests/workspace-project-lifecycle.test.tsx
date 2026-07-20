import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceHome } from "../src/components/projects/workspace-home";
import { ProjectOverview } from "../src/components/projects/project-overview";

const push = vi.fn();
const listWorkspaces = vi.fn();
const listProjects = vi.fn();
const createProject = vi.fn();
const getProjectOverview = vi.fn();
const updateProject = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("../src/lib/workspaces/api", () => ({
  listWorkspaces: (...args: unknown[]) => listWorkspaces(...args),
}));
vi.mock("../src/lib/projects/api", () => ({
  ProjectApiError: class ProjectApiError extends Error {},
  listProjects: (...args: unknown[]) => listProjects(...args),
  createProject: (...args: unknown[]) => createProject(...args),
  getProjectOverview: (...args: unknown[]) => getProjectOverview(...args),
  updateProject: (...args: unknown[]) => updateProject(...args),
}));

const workspace = {
  workspace_id: "workspace-1",
  organization_id: "organization-1",
  name: "Northstar Measurement",
  slug: "northstar-measurement",
  role: "owner",
};

const project = {
  id: "project-1",
  workspace_id: "workspace-1",
  created_by_user_id: "user-1",
  name: "Paid Search Lift",
  slug: "paid-search-lift",
  description: "Measures Q3 search investment.",
  status: "active",
  created_at: "2026-07-18T12:00:00Z",
  archived_at: null,
};

beforeEach(() => {
  localStorage.setItem("incrementality_session_token", "session-token");
  listWorkspaces.mockResolvedValue([workspace]);
  listProjects.mockResolvedValue([project]);
  getProjectOverview.mockResolvedValue({
    ...project,
    latest_dataset_id: null,
    latest_dataset_status: null,
    semantic_mapping_configured: false,
    latest_analysis_run_id: null,
    latest_analysis_run_status: null,
  });
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});

describe("workspace project lifecycle", () => {
  it("renders the real workspace identity and its projects", async () => {
    render(<WorkspaceHome workspaceId="workspace-1" />);

    expect(await screen.findByRole("heading", { name: "Northstar Measurement" })).toBeInTheDocument();
    expect(screen.getByText("Owner")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Paid Search Lift/i })).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1",
    );
    expect(screen.getByText("Measures Q3 search investment.")).toBeInTheDocument();
  });

  it("creates a project once and routes to its canonical overview", async () => {
    listProjects.mockResolvedValueOnce([]);
    createProject.mockResolvedValueOnce(project);
    render(<WorkspaceHome workspaceId="workspace-1" />);

    fireEvent.click(await screen.findByRole("button", { name: /new project/i }));
    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "Paid Search Lift" },
    });
    fireEvent.change(screen.getByLabelText("Project URL"), {
      target: { value: "paid-search-lift" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Measures Q3 search investment." },
    });
    const submit = screen.getByRole("button", { name: "Create project" });
    fireEvent.click(submit);
    fireEvent.click(submit);

    await waitFor(() => expect(createProject).toHaveBeenCalledTimes(1));
    expect(createProject).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      {
        name: "Paid Search Lift",
        slug: "paid-search-lift",
        description: "Measures Q3 search investment.",
      },
    );
    expect(push).toHaveBeenCalledWith(
      "/workspaces/workspace-1/projects/project-1",
    );
  });

  it("keeps project creation failures safe and recoverable", async () => {
    listProjects.mockResolvedValueOnce([]);
    createProject.mockRejectedValueOnce(new Error("private database detail"));
    render(<WorkspaceHome workspaceId="workspace-1" />);

    fireEvent.click(await screen.findByRole("button", { name: /new project/i }));
    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "Paid Search Lift" },
    });
    fireEvent.change(screen.getByLabelText("Project URL"), {
      target: { value: "paid-search-lift" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create project" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We couldn't create this project. Please try again.",
    );
    expect(screen.queryByText("private database detail")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create project" })).toBeEnabled();
  });

  it("shows an honest empty state and can recover from load failure", async () => {
    listProjects.mockRejectedValueOnce(new Error("offline"));
    render(<WorkspaceHome workspaceId="workspace-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We couldn't load this workspace",
    );

    listProjects.mockResolvedValueOnce([]);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("No projects yet")).toBeInTheDocument();
  });

  it("opens a project overview and switches without preserving stale project context", async () => {
    const secondProject = { ...project, id: "project-2", name: "Geo Holdout", slug: "geo-holdout" };
    listProjects.mockResolvedValueOnce([project, secondProject]);
    render(<ProjectOverview workspaceId="workspace-1" projectId="project-1" />);

    expect(await screen.findByRole("heading", { name: "Paid Search Lift" })).toBeInTheDocument();
    expect(screen.getByText("Add data to continue")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Switch project"), {
      target: { value: "project-2" },
    });

    expect(push).toHaveBeenCalledWith(
      "/workspaces/workspace-1/projects/project-2",
    );
  });

  it("shows an Upload Dataset entry point when the project has no dataset", async () => {
    render(<ProjectOverview workspaceId="workspace-1" projectId="project-1" />);

    expect(
      await screen.findByText("No dataset uploaded"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Upload Dataset" }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/upload",
    );
  });

  it("renames a project while preserving its canonical URL", async () => {
    updateProject.mockResolvedValueOnce({ ...project, name: "Search Incrementality" });
    render(<ProjectOverview workspaceId="workspace-1" projectId="project-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Edit project" }));
    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "Search Incrementality" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByRole("heading", { name: "Search Incrementality" })).toBeInTheDocument();
    expect(updateProject).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      {
        name: "Search Incrementality",
        description: "Measures Q3 search investment.",
      },
    );
    expect(screen.getByText("paid-search-lift")).toBeInTheDocument();
  });

  it("shows Explore Dataset when the project's latest dataset is ready", async () => {
    getProjectOverview.mockResolvedValueOnce({
      ...project,
      latest_dataset_id: "dataset-1",
      latest_dataset_status: "ready",
      semantic_mapping_configured: false,
      latest_analysis_run_id: null,
      latest_analysis_run_status: null,
    });

    render(
      <ProjectOverview
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText("Dataset ready"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Explore Dataset" }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/explore",
    );

    expect(
      screen.getByRole("link", { name: "View Data Quality" }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/quality",
    );
  });


  it("shows validation in progress when the latest dataset is validating", async () => {
    getProjectOverview.mockResolvedValueOnce({
      ...project,
      latest_dataset_id: "dataset-1",
      latest_dataset_status: "validating",
      semantic_mapping_configured: false,
      latest_analysis_run_id: null,
      latest_analysis_run_status: null,
    });

    render(
      <ProjectOverview
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText("Validation in progress"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "View Status" }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/upload",
    );
  });


  it("shows upload pending when the latest dataset is pending upload", async () => {
    getProjectOverview.mockResolvedValueOnce({
      ...project,
      latest_dataset_id: "dataset-1",
      latest_dataset_status: "pending_upload",
      semantic_mapping_configured: false,
      latest_analysis_run_id: null,
      latest_analysis_run_status: null,
    });

    render(
      <ProjectOverview
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText("Upload pending"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Resume Upload" }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/upload",
    );
  });


  it("shows validation pending when the latest dataset is uploaded", async () => {
    getProjectOverview.mockResolvedValueOnce({
      ...project,
      latest_dataset_id: "dataset-1",
      latest_dataset_status: "uploaded",
      semantic_mapping_configured: false,
      latest_analysis_run_id: null,
      latest_analysis_run_status: null,
    });

    render(
      <ProjectOverview
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText("Validation pending"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "View Status" }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/upload",
    );
  });


  it("shows validation failed when the latest dataset failed validation", async () => {
    getProjectOverview.mockResolvedValueOnce({
      ...project,
      latest_dataset_id: "dataset-1",
      latest_dataset_status: "failed",
      semantic_mapping_configured: false,
      latest_analysis_run_id: null,
      latest_analysis_run_status: null,
    });

    render(
      <ProjectOverview
        workspaceId="workspace-1"
        projectId="project-1"
      />,
    );

    expect(
      await screen.findByText("Dataset validation failed"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Review Failure" }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/upload",
    );
  });


  it("keeps project creation read-only for viewers", async () => {
    listWorkspaces.mockResolvedValueOnce([
      {
        ...workspace,
        role: "viewer",
      },
    ]);

    listProjects.mockResolvedValueOnce([]);

    render(
      <WorkspaceHome
        workspaceId="workspace-1"
      />,
    );

    expect(
      await screen.findByRole(
        "heading",
        {
          name: "Northstar Measurement",
        },
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole(
        "button",
        {
          name: /new project/i,
        },
      ),
    ).not.toBeInTheDocument();

    expect(
      screen.queryByRole(
        "button",
        {
          name: /create your first project/i,
        },
      ),
    ).not.toBeInTheDocument();

    expect(
      screen.getByText(
        "No projects yet",
      ),
    ).toBeInTheDocument();
  });

  it("keeps project editing read-only for viewers", async () => {
    listWorkspaces.mockResolvedValueOnce([
      {
        ...workspace,
        role: "viewer",
      },
    ]);

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
          name: "Paid Search Lift",
        },
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole(
        "button",
        {
          name: "Edit project",
        },
      ),
    ).not.toBeInTheDocument();
  });

});
