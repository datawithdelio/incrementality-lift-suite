import type { AnalysisRunLineageResponse } from "./lineage-types";
import type { AnalysisResultResponse } from "./types";

export class ResultsApiError extends Error {
  constructor(public readonly status: number) {
    super("Unable to retrieve analysis result.");
  }
}

export async function fetchAnalysisResult(
  workspaceId: string,
  projectId: string,
  analysisRunId: string,
  token: string,
  signal?: AbortSignal,
): Promise<AnalysisResultResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  const response = await fetch(
    `${baseUrl}/api/v1/workspaces/${workspaceId}/projects/${projectId}/analysis-runs/${analysisRunId}/result`,
    {
      headers: { Authorization: `Bearer ${token}` },
      signal,
      cache: "no-store",
    },
  );
  if (!response.ok) throw new ResultsApiError(response.status);
  return (await response.json()) as AnalysisResultResponse;
}



export async function fetchAnalysisLineage(
  workspaceId: string,
  projectId: string,
  analysisRunId: string,
  token: string,
  signal?: AbortSignal,
): Promise<AnalysisRunLineageResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  const response = await fetch(
    `${baseUrl}/api/v1/workspaces/${workspaceId}/projects/${projectId}/analysis-runs/${analysisRunId}/lineage`,
    {
      headers: { Authorization: `Bearer ${token}` },
      signal,
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ResultsApiError(response.status);
  }

  return (await response.json()) as AnalysisRunLineageResponse;
}
