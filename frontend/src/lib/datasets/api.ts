export type DatasetStatus =
  "pending_upload" | "uploaded" | "validating" | "ready" | "failed";

export type Dataset = {
  id: string;
  workspace_id: string;
  project_id: string;
  created_by_user_id: string;
  source_filename: string;
  storage_key: string;
  media_type: string;
  byte_size: number;
  checksum_sha256: string;
  status: DatasetStatus;
  created_at: string;
  uploaded_at: string | null;
  validation_started_at: string | null;
  validation_completed_at: string | null;
  row_count: number | null;
  column_count: number | null;
  failure_reason: string | null;
};

export type RegisterDatasetInput = {
  source_filename: string;
  media_type: "text/csv";
  byte_size: number;
  checksum_sha256: string;
};

export class DatasetApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null = null,
  ) {
    super(message);
  }
}

export function datasetCollectionPath(
  workspaceId: string,
  projectId: string,
): string {
  return `/api/v1/workspaces/${workspaceId}/projects/${projectId}/datasets`;
}

export function datasetResourcePath(
  workspaceId: string,
  projectId: string,
  datasetId: string,
): string {
  return `${datasetCollectionPath(workspaceId, projectId)}/${datasetId}`;
}

export function datasetContentPath(
  workspaceId: string,
  projectId: string,
  datasetId: string,
): string {
  return `${datasetResourcePath(workspaceId, projectId, datasetId)}/content`;
}

async function errorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  const payload = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;

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
    throw new DatasetApiError(
      `${fallback} Check your connection and try again.`,
    );
  }

  if (!response.ok) {
    throw new DatasetApiError(
      await errorMessage(response, fallback),
      response.status,
    );
  }

  return (await response.json()) as T;
}

export function registerDataset(
  token: string,
  workspaceId: string,
  projectId: string,
  input: RegisterDatasetInput,
): Promise<Dataset> {
  return request<Dataset>(
    datasetCollectionPath(workspaceId, projectId),
    token,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
    "We couldn't initialize the dataset upload.",
  );
}

export function uploadDatasetContent(
  token: string,
  workspaceId: string,
  projectId: string,
  datasetId: string,
  file: File,
  options: {
    restoreMissing?: boolean;
  } = {},
): Promise<Dataset> {
  const contentPath = datasetContentPath(workspaceId, projectId, datasetId);

  return request<Dataset>(
    options.restoreMissing
      ? `${contentPath}?restore_missing=true`
      : contentPath,
    token,
    {
      method: "PUT",
      headers: {
        "Content-Type": "text/csv",
      },
      body: file,
    },
    "We couldn't upload the dataset.",
  );
}

export function getDataset(
  token: string,
  workspaceId: string,
  projectId: string,
  datasetId: string,
): Promise<Dataset> {
  return request<Dataset>(
    datasetResourcePath(workspaceId, projectId, datasetId),
    token,
    {
      method: "GET",
      cache: "no-store",
    },
    "We couldn't load the dataset.",
  );
}
