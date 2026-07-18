import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createProject,
  getProject,
  getProjectOverview,
  listProjects,
  updateProject,
} from "../src/lib/projects/api";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

const project = {
  id: "project-1",
  workspace_id: "workspace-1",
  created_by_user_id: "user-1",
  name: "Paid Search Lift",
  slug: "paid-search-lift",
  description: "Q3 study",
  status: "active" as const,
  created_at: "2026-07-18T12:00:00Z",
  archived_at: null,
};

describe("project API", () => {
  it("lists projects inside the active workspace", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify([project]), { status: 200 }),
    );

    await expect(listProjects("token", "workspace-1")).resolves.toEqual([project]);
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects",
      {
        method: "GET",
        headers: { Authorization: "Bearer token" },
        cache: "no-store",
      },
    );
  });

  it("creates a project from server-supported fields", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(project), { status: 201 }),
    );

    await createProject("token", "workspace-1", {
      name: "Paid Search Lift",
      slug: "paid-search-lift",
      description: "Q3 study",
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "Paid Search Lift",
          slug: "paid-search-lift",
          description: "Q3 study",
        }),
      }),
    );
  });

  it("opens and updates a deterministic workspace-scoped project", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify(project), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...project, name: "Renamed" }), { status: 200 }),
      );

    await getProject("token", "workspace-1", "project-1");
    await updateProject("token", "workspace-1", "project-1", {
      name: "Renamed",
      description: null,
    });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/workspaces/workspace-1/projects/project-1",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/workspaces/workspace-1/projects/project-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ name: "Renamed", description: null }),
      }),
    );
  });

  it("loads the persisted workflow snapshot for next-action decisions", async () => {
    const overview = {
      ...project,
      latest_dataset_id: "dataset-1",
      latest_dataset_status: "ready",
      semantic_mapping_configured: true,
      latest_analysis_run_id: "run-1",
      latest_analysis_run_status: "running",
    };
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(overview), { status: 200 }),
    );

    await expect(
      getProjectOverview("token", "workspace-1", "project-1"),
    ).resolves.toEqual(overview);
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects/project-1/overview",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
