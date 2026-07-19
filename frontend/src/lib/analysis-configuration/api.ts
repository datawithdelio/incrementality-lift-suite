import type {
  AnalysisEstimatorType,
  QueueAnalysisRunRequest,
} from "./request";

export type AnalysisRunResponse = {
  id: string;
  workspace_id: string;
  project_id: string;

  dataset_id?: string;
  semantic_mapping_id?: string;
  semantic_mapping_version?: number;
  created_by_user_id?: string;

  estimator_type:
    AnalysisEstimatorType;

  estimator_version?: string;

  configuration?: Record<
    string,
    unknown
  >;

  status: string;

  created_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
  failure_reason?: string | null;
  cancellation_reason?: string | null;
};

export class AnalysisRunApiError
  extends Error {
  constructor(
    message: string,
    readonly status:
      number | null = null,
  ) {
    super(message);

    this.name =
      "AnalysisRunApiError";
  }
}

async function errorMessage(
  response: Response,
): Promise<string> {
  const payload =
    await response
      .json()
      .catch(() => null) as
      | {
          detail?: string;
        }
      | null;

  return (
    payload?.detail
    ?? "We couldn't queue this analysis."
  );
}

export async function queueAnalysisRun(
  token: string,
  workspaceId: string,
  projectId: string,
  request:
    QueueAnalysisRunRequest,
): Promise<AnalysisRunResponse> {
  let response: Response;

  try {
    response = await fetch(
      `/api/v1/workspaces/${workspaceId}/projects/${projectId}/analysis-runs`,
      {
        method: "POST",

        headers: {
          Authorization:
            `Bearer ${token}`,

          "Content-Type":
            "application/json",
        },

        body: JSON.stringify(
          request,
        ),

        cache: "no-store",
      },
    );
  } catch {
    throw new AnalysisRunApiError(
      "We couldn't queue this analysis. Check your connection and try again.",
    );
  }

  if (!response.ok) {
    throw new AnalysisRunApiError(
      await errorMessage(
        response,
      ),
      response.status,
    );
  }

  return (
    await response.json()
  ) as AnalysisRunResponse;
}


export function humanizeAnalysisRunQueueError(
  error: unknown,
): string {
  if (!(error instanceof AnalysisRunApiError)) {
    return (
      "We couldn't queue this analysis right now. "
      + "Try again."
    );
  }

  switch (error.status) {
    case null:
      return (
        "We couldn't queue this analysis. "
        + "Check your connection and try again."
      );

    case 401:
      return (
        "Your session has expired. "
        + "Sign in again and retry."
      );

    case 403:
      return (
        "You don't have permission to queue "
        + "analyses for this project."
      );

    case 404:
      return (
        "The dataset or semantic mapping is no "
        + "longer available. Refresh the project "
        + "and review the latest data."
      );

    case 409:
      return (
        "Your analysis could not be queued because "
        + "the dataset or configuration changed. "
        + "Review the latest project data and try again."
      );

    case 422:
      return (
        "Some analysis settings are no longer valid. "
        + "Review the configuration and try again."
      );

    default:
      return (
        "We couldn't queue this analysis right now. "
        + "Try again."
      );
  }
}
