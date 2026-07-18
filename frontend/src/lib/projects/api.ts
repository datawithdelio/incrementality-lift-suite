export type Project = {
  id: string;
  workspace_id: string;
  created_by_user_id: string;
  name: string;
  slug: string;
  description: string | null;
  status: "active" | "archived";
  created_at: string;
  archived_at: string | null;
};

export type ProjectInput = {
  name: string;
  slug: string;
  description: string | null;
};

export type ProjectUpdate = Pick<ProjectInput, "name" | "description">;

export type ProjectOverview = Project & {
  latest_dataset_id: string | null;
  latest_dataset_status: string | null;
  semantic_mapping_configured: boolean;
  latest_analysis_run_id: string | null;
  latest_analysis_run_status: string | null;
};

export class ProjectApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null = null,
  ) {
    super(message);
  }
}

function projectCollectionPath(workspaceId: string): string {
  return `/api/v1/workspaces/${workspaceId}/projects`;
}

function projectResourcePath(workspaceId: string, projectId: string): string {
  return `${projectCollectionPath(workspaceId)}/${projectId}`;
}

async function errorMessage(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => null) as { detail?: string } | null;
  return payload?.detail ?? fallback;
}

async function request<T>(
  path: string,
  token: string,
  init: RequestInit,
  fallback: string,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        ...init.headers,
      },
    });
  } catch {
    throw new ProjectApiError(`${fallback} Check your connection and try again.`);
  }

  if (!response.ok) {
    throw new ProjectApiError(
      await errorMessage(response, fallback),
      response.status,
    );
  }

  return await response.json() as T;
}

export function listProjects(token: string, workspaceId: string): Promise<Project[]> {
  return request<Project[]>(
    projectCollectionPath(workspaceId),
    token,
    { method: "GET", cache: "no-store" },
    "We couldn't load this workspace's projects.",
  );
}

export function getProject(
  token: string,
  workspaceId: string,
  projectId: string,
): Promise<Project> {
  return request<Project>(
    projectResourcePath(workspaceId, projectId),
    token,
    { method: "GET", cache: "no-store" },
    "We couldn't load this project.",
  );
}

export function getProjectOverview(
  token: string,
  workspaceId: string,
  projectId: string,
): Promise<ProjectOverview> {
  return request<ProjectOverview>(
    `${projectResourcePath(workspaceId, projectId)}/overview`,
    token,
    { method: "GET", cache: "no-store" },
    "We couldn't load this project.",
  );
}

export function createProject(
  token: string,
  workspaceId: string,
  input: ProjectInput,
): Promise<Project> {
  return request<Project>(
    projectCollectionPath(workspaceId),
    token,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
    "We couldn't create this project.",
  );
}

export function updateProject(
  token: string,
  workspaceId: string,
  projectId: string,
  input: ProjectUpdate,
): Promise<Project> {
  return request<Project>(
    projectResourcePath(workspaceId, projectId),
    token,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
    "We couldn't update this project.",
  );
}
