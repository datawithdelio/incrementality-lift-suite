import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createWorkspace,
  listWorkspaceMembers,
  listWorkspaces,
} from "../src/lib/workspaces/api";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

describe("workspace API", () => {
  it("lists workspaces using the authenticated bearer session", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          {
            workspace_id: "workspace-1",
            organization_id: "organization-1",
            name: "Measurement Team",
            slug: "measurement-team",
            role: "owner",
          },
        ]),
        { status: 200 },
      ),
    );

    const result = await listWorkspaces(
      "session-token",
    );

    expect(result).toEqual([
      {
        workspace_id: "workspace-1",
        organization_id: "organization-1",
        name: "Measurement Team",
        slug: "measurement-team",
        role: "owner",
      },
    ]);

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/workspaces",
      {
        method: "GET",
        headers: {
          Authorization: "Bearer session-token",
        },
        cache: "no-store",
      },
    );
  });

  it("lists members inside the authorized workspace scope", async () => {
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

    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify(members),
        { status: 200 },
      ),
    );

    await expect(
      listWorkspaceMembers(
        "session-token",
        "workspace-1",
      ),
    ).resolves.toEqual(members);

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/members",
      {
        method: "GET",
        headers: {
          Authorization: "Bearer session-token",
        },
        cache: "no-store",
      },
    );
  });

  it("creates a workspace using the authenticated bearer session", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          organization_id: "organization-1",
          workspace_id: "workspace-1",
          membership_id: "membership-1",
        }),
        { status: 201 },
      ),
    );

    const result = await createWorkspace(
      "session-token",
      {
        organizationName: "Northstar Labs",
        workspaceName: "Measurement Team",
      },
    );

    expect(result.workspace_id).toBe(
      "workspace-1",
    );

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/workspaces",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer session-token",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          organization_name: "Northstar Labs",
          workspace_name: "Measurement Team",
        }),
      },
    );
  });

  it("explains when the organization slug is already in use", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: "A workspace with this information already exists.",
        }),
        { status: 409 },
      ),
    );

    await expect(
      createWorkspace(
        "session-token",
        {
          organizationName: "Northstar Labs",
          workspaceName: "Measurement Team",
        },
      ),
    ).rejects.toThrow(
      "This organization URL is already in use. Choose a different organization name.",
    );
  });
});
