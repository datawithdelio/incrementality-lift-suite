import type { DataQuality, DatasetPreview, DatasetVersion, ReportJob } from "./types";

export class DataProductApiError extends Error { constructor(public status: number) { super("Data product is unavailable."); } }
async function request<T>(path: string, token: string, init: RequestInit = {}): Promise<T> { const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}${path}`, { ...init, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...init.headers }, cache: "no-store" }); if (!response.ok) throw new DataProductApiError(response.status); return await response.json() as T; }
export type ExplorerOptions = {
  page: number;
  search: string;
  sortColumn: string;
  descending: boolean;
  filterColumn: string;
  filterOperator?: "contains" | "is_missing";
  filterValue: string;
  outcomeColumn?: string;
};

export function fetchPreview(
  workspace: string,
  project: string,
  dataset: string,
  options: ExplorerOptions,
  token: string,
  signal: AbortSignal,
) {
  const query = new URLSearchParams({
    page: String(options.page),
    column_search: options.search,
    descending: String(options.descending),
  });
  if (options.sortColumn) {
    query.set("sort_column", options.sortColumn);
  }
  if (options.filterColumn) {
    query.set("filter_column", options.filterColumn);
    const operator = options.filterOperator ?? "contains";
    query.set("filter_operator", operator);
    if (operator === "contains") {
      query.set("filter_value", options.filterValue);
    }
  }
  if (options.outcomeColumn) {
    query.set("outcome_column", options.outcomeColumn);
  }
  return request<DatasetPreview>(
    `/api/v1/workspaces/${workspace}/projects/${project}`
      + `/datasets/${dataset}/preview?${query}`,
    token,
    { signal },
  );
}
export function fetchDatasetVersions(workspace: string, project: string, token: string, signal: AbortSignal) { return request<DatasetVersion[]>(`/api/v1/workspaces/${workspace}/projects/${project}/dataset-versions`, token, { signal }); }
export function assessQuality(workspace: string, project: string, dataset: string, estimator: string, token: string, signal: AbortSignal) { return request<DataQuality>(`/api/v1/workspaces/${workspace}/projects/${project}/datasets/${dataset}/quality?estimator=${estimator}`, token, { method: "POST", signal }); }
export function fetchReports(workspace: string, project: string, run: string, token: string, signal: AbortSignal) { return request<ReportJob[]>(`/api/v1/workspaces/${workspace}/projects/${project}/analysis-runs/${run}/reports`, token, { signal }); }
export function queueReport(workspace: string, project: string, run: string, format: string, token: string) { return request<ReportJob>(`/api/v1/workspaces/${workspace}/projects/${project}/analysis-runs/${run}/reports`, token, { method: "POST", body: JSON.stringify({ format }) }); }

export type ReportDownload = {
  blob: Blob;
  filename: string;
};

function reportDownloadFilename(
  contentDisposition: string | null,
): string {
  if (!contentDisposition) {
    return "analysis-report";
  }

  const utf8Match = contentDisposition.match(
    /filename\*=UTF-8''([^;]+)/i,
  );

  if (utf8Match?.[1]) {
    return decodeURIComponent(
      utf8Match[1],
    );
  }

  const quotedMatch = contentDisposition.match(
    /filename="([^"]+)"/i,
  );

  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  const plainMatch = contentDisposition.match(
    /filename=([^;]+)/i,
  );

  return plainMatch?.[1]?.trim()
    ?? "analysis-report";
}

export async function downloadReport(
  workspace: string,
  project: string,
  run: string,
  report: string,
  token: string,
): Promise<ReportDownload> {
  const path =
    `/api/v1/workspaces/${workspace}` +
    `/projects/${project}` +
    `/analysis-runs/${run}` +
    `/reports/${report}/download`;

  let response: Response;

  try {
    response = await fetch(
      `${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}${path}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      },
    );
  } catch {
    throw new DataProductApiError(0);
  }

  if (!response.ok) {
    throw new DataProductApiError(
      response.status,
    );
  }

  return {
    blob: await response.blob(),
    filename: reportDownloadFilename(
      response.headers.get(
        "Content-Disposition",
      ),
    ),
  };
}
