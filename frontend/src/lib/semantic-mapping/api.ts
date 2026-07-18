export type SemanticMapping = {
  id: string;
  dataset_id: string;
  created_by_user_id: string;
  version: number;
  time_column: string;
  unit_column: string;
  treatment_column: string;
  outcome_column: string;
  spend_column: string | null;
  covariate_columns: string[];
  treatment_value: string;
  control_value: string;
  created_at: string;
  updated_at: string;
};

export class SemanticMappingApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null = null,
  ) {
    super(message);
  }
}

export function semanticMappingCollectionPath(
  workspaceId: string,
  projectId: string,
  datasetId: string,
): string {
  return (
    `/api/v1/workspaces/${workspaceId}`
    + `/projects/${projectId}`
    + `/datasets/${datasetId}`
    + "/semantic-mappings"
  );
}

export function latestSemanticMappingPath(
  workspaceId: string,
  projectId: string,
  datasetId: string,
): string {
  return (
    `${semanticMappingCollectionPath(
      workspaceId,
      projectId,
      datasetId,
    )}/latest`
  );
}

async function errorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  const payload = await response
    .json()
    .catch(() => null) as {
      detail?: string;
    } | null;

  return payload?.detail ?? fallback;
}

export async function getLatestSemanticMapping(
  token: string,
  workspaceId: string,
  projectId: string,
  datasetId: string,
): Promise<SemanticMapping | null> {
  let response: Response;

  try {
    response = await fetch(
      latestSemanticMappingPath(
        workspaceId,
        projectId,
        datasetId,
      ),
      {
        method: "GET",
        cache: "no-store",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );
  } catch {
    throw new SemanticMappingApiError(
      "We couldn't load the semantic mapping. Check your connection and try again.",
    );
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new SemanticMappingApiError(
      await errorMessage(
        response,
        "We couldn't load the semantic mapping.",
      ),
      response.status,
    );
  }

  return await response.json() as SemanticMapping;
}

export type CreateSemanticMappingInput = {
  time_column: string;
  unit_column: string;
  treatment_column: string;
  outcome_column: string;
  spend_column: string | null;
  covariate_columns: string[];
  treatment_value: string;
  control_value: string;
};

async function semanticMappingSaveErrorMessage(
  response: Response,
): Promise<string> {
  try {
    const payload = await response.json() as {
      detail?: unknown;
    };

    if (
      typeof payload.detail === "string"
      && payload.detail.trim().length > 0
    ) {
      return payload.detail;
    }
  } catch {
    // Fall through to the status-based message.
  }

  return "Semantic mapping could not be saved.";
}

export async function createSemanticMapping(
  token: string,
  workspaceId: string,
  projectId: string,
  datasetId: string,
  request: CreateSemanticMappingInput,
): Promise<SemanticMapping> {
  let response: Response;

  try {
    response = await fetch(
      semanticMappingCollectionPath(
        workspaceId,
        projectId,
        datasetId,
      ),
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      },
    );
  } catch {
    throw new SemanticMappingApiError(
      "Unable to connect while saving the semantic mapping.",
      null,
    );
  }

  if (!response.ok) {
    throw new SemanticMappingApiError(
      await semanticMappingSaveErrorMessage(
        response,
      ),
      response.status,
    );
  }

  return await response.json() as SemanticMapping;
}
