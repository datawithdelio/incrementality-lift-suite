import type {
  DataQuality,
  DatasetPreview,
  DatasetVersion,
  GeographySummary,
  ReportJob,
} from "./types";

export class DataProductApiError extends Error {
  constructor(
    public status: number,
    public detail?: string,
  ) {
    super("Data product is unavailable.");
  }
}
async function request<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}${path}`,
    {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        ...init.headers,
      },
      cache: "no-store",
    },
  );
  if (!response.ok) {
    let detail: string | undefined;

    try {
      const body = (await response.json()) as { detail?: unknown };
      detail = typeof body.detail === "string" ? body.detail : undefined;
    } catch {
      // Error bodies are not guaranteed to be JSON.
    }

    throw new DataProductApiError(response.status, detail);
  }
  return (await response.json()) as T;
}
export type ExplorerOptions = {
  page: number;
  search: string;
  sortColumn: string;
  descending: boolean;
  filterColumn: string;
  filterOperator?: "contains" | "is_missing";
  filterValue: string;
  outcomeColumn?: string;
  interventionDate?: string;
  estimator?: string;
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

  if (options.interventionDate) {
    query.set("intervention_date", options.interventionDate);
  }
  if (options.estimator) {
    query.set("estimator", options.estimator);
  }
  return request<DatasetPreview>(
    `/api/v1/workspaces/${workspace}/projects/${project}` +
      `/datasets/${dataset}/preview?${query}`,
    token,
    { signal },
  );
}
export function fetchGeographySummary(
  workspace: string,
  project: string,
  dataset: string,
  mappingVersion: number,
  token: string,
  signal: AbortSignal,
) {
  const query = new URLSearchParams({
    mapping_version: String(mappingVersion),
  });

  return request<GeographySummary>(
    `/api/v1/workspaces/${workspace}/projects/${project}` +
      `/datasets/${dataset}/geography-summary?${query}`,
    token,
    { signal },
  );
}

export function fetchDatasetVersions(
  workspace: string,
  project: string,
  token: string,
  signal: AbortSignal,
) {
  return request<DatasetVersion[]>(
    `/api/v1/workspaces/${workspace}/projects/${project}/dataset-versions`,
    token,
    { signal },
  );
}
export function assessQuality(
  workspace: string,
  project: string,
  dataset: string,
  estimator: string,
  token: string,
  signal: AbortSignal,
) {
  return request<DataQuality>(
    `/api/v1/workspaces/${workspace}/projects/${project}/datasets/${dataset}/quality?estimator=${estimator}`,
    token,
    { method: "POST", signal },
  );
}
export function fetchReports(
  workspace: string,
  project: string,
  run: string,
  token: string,
  signal: AbortSignal,
) {
  return request<ReportJob[]>(
    `/api/v1/workspaces/${workspace}/projects/${project}/analysis-runs/${run}/reports`,
    token,
    { signal },
  );
}
export function queueReport(
  workspace: string,
  project: string,
  run: string,
  format: string,
  token: string,
) {
  return request<ReportJob>(
    `/api/v1/workspaces/${workspace}/projects/${project}/analysis-runs/${run}/reports`,
    token,
    { method: "POST", body: JSON.stringify({ format }) },
  );
}

export type ReportDownload = {
  blob: Blob;
  filename: string;
};

function reportDownloadFilename(contentDisposition: string | null): string {
  if (!contentDisposition) {
    return "analysis-report";
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);

  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const quotedMatch = contentDisposition.match(/filename="([^"]+)"/i);

  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  const plainMatch = contentDisposition.match(/filename=([^;]+)/i);

  return plainMatch?.[1]?.trim() ?? "analysis-report";
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

  const controller = new AbortController();

  const timeoutId = globalThis.setTimeout(() => {
    controller.abort();
  }, 30_000);

  try {
    let response: Response;

    try {
      response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}${path}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          cache: "no-store",
          signal: controller.signal,
        },
      );
    } catch {
      throw new DataProductApiError(0);
    }

    if (!response.ok) {
      throw new DataProductApiError(response.status);
    }

    let blob: Blob;

    try {
      blob = await response.blob();
    } catch {
      throw new DataProductApiError(0);
    }

    if (blob.size === 0) {
      throw new DataProductApiError(502);
    }

    return {
      blob,
      filename: reportDownloadFilename(
        response.headers.get("Content-Disposition"),
      ),
    };
  } finally {
    globalThis.clearTimeout(timeoutId);
  }
}
