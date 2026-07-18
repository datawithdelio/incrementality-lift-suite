export type AccessibleWorkspace = {
  workspace_id: string;
  organization_id: string;
  name: string;
  slug: string;
  role: string;
};

export type CreatedWorkspace = {
  organization_id: string;
  workspace_id: string;
  membership_id: string;
};

export class WorkspaceApiError extends Error {}

async function readErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  const payload = await response
    .json()
    .catch(() => null) as { detail?: string } | null;

  return payload?.detail ?? fallback;
}

export async function listWorkspaces(
  token: string,
): Promise<AccessibleWorkspace[]> {
  let response: Response;

  try {
    response = await fetch(
      "/api/v1/workspaces",
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      },
    );
  } catch {
    throw new WorkspaceApiError(
      "We couldn't load your workspaces. Please check your connection and try again.",
    );
  }

  if (!response.ok) {
    throw new WorkspaceApiError(
      await readErrorMessage(
        response,
        "We couldn't load your workspaces.",
      ),
    );
  }

  return await response.json() as AccessibleWorkspace[];
}

export async function createWorkspace(
  token: string,
  input: {
    organizationName: string;
    workspaceName: string;
  },
): Promise<CreatedWorkspace> {
  let response: Response;

  try {
    response = await fetch(
      "/api/v1/workspaces",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          organization_name: input.organizationName,
          workspace_name: input.workspaceName,
        }),
      },
    );
  } catch {
    throw new WorkspaceApiError(
      "We couldn't create your workspace. Please check your connection and try again.",
    );
  }

  if (!response.ok) {
    throw new WorkspaceApiError(
      await readErrorMessage(
        response,
        "We couldn't create your workspace.",
      ),
    );
  }

  return await response.json() as CreatedWorkspace;
}
