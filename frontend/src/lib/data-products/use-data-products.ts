"use client";
import { useEffect, useState } from "react";
import { getDataset } from "../datasets/api";
import { datasetUploadPath } from "../projects/routes";
import {
  assessQuality,
  DataProductApiError,
  ExplorerOptions,
  fetchDatasetVersions,
  fetchPreview,
  fetchReports,
} from "./api";
import type {
  DataQuality,
  DatasetPreview,
  DatasetVersion,
  LoadState,
  ReportJob,
} from "./types";
type DataProductFailure = "permission" | "error";

type DatasetExplorerFailure = DataProductFailure | "unavailable";

const INVALID_INTERVENTION_DETAIL =
  "Intervention date must fall inside the dataset date range.";

const failure = (error: unknown): DataProductFailure => {
  if (
    error instanceof DataProductApiError &&
    [401, 403].includes(error.status)
  ) {
    return "permission";
  }

  return "error";
};

const explorerFailure = (error: unknown): DatasetExplorerFailure => {
  if (error instanceof DataProductApiError && error.status === 404) {
    return "unavailable";
  }

  return failure(error);
};

const isInvalidInterventionError = (error: unknown): boolean =>
  error instanceof DataProductApiError &&
  error.status === 422 &&
  error.detail === INVALID_INTERVENTION_DETAIL;

export function useDatasetExplorer(
  workspace: string,
  project: string,
  dataset: string,
  options: ExplorerOptions,
  estimator: string,
  onInvalidInterventionDate?: (value: string) => void,
) {
  const [state, setState] = useState<
    | LoadState<DatasetPreview>
    | {
        kind: "unavailable";
        uploadHref: string;
      }
  >({
    kind: "loading",
  });

  const [quality, setQuality] = useState<DataQuality>();

  const [versions, setVersions] = useState<DatasetVersion[]>([]);

  const [datasetMetadata, setDatasetMetadata] =
    useState<Awaited<ReturnType<typeof getDataset>>>();

  useEffect(() => {
    const controller = new AbortController();
    const token = localStorage.getItem("incrementality_session_token");

    if (!token) {
      queueMicrotask(() =>
        setState({
          kind: "permission",
        }),
      );

      return;
    }

    const sessionToken = token;

    queueMicrotask(() => {
      if (!controller.signal.aborted) {
        setState({
          kind: "loading",
        });
      }
    });

    async function loadExplorer(): Promise<void> {
      try {
        /*
         * Preview is the authoritative availability check.
         * Load it first so a missing CSV produces the recovery
         * experience instead of being masked by a secondary
         * quality-request failure.
         */
        const preview = await fetchPreview(
          workspace,
          project,
          dataset,
          options,
          sessionToken,
          controller.signal,
        );

        if (controller.signal.aborted) {
          return;
        }

        setState({
          kind: "ready",
          data: preview,
        });

        const [assessment, datasetVersions, datasetRecord] = await Promise.all([
          assessQuality(
            workspace,
            project,
            dataset,
            estimator,
            sessionToken,
            controller.signal,
          ),
          fetchDatasetVersions(
            workspace,
            project,
            sessionToken,
            controller.signal,
          ),
          getDataset(sessionToken, workspace, project, dataset),
        ]);

        if (controller.signal.aborted) {
          return;
        }

        setQuality(assessment);
        setVersions(datasetVersions);
        setDatasetMetadata(datasetRecord);
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        if (
          options.interventionDate &&
          onInvalidInterventionDate &&
          isInvalidInterventionError(error)
        ) {
          onInvalidInterventionDate(options.interventionDate);
          return;
        }

        const kind = explorerFailure(error);

        if (kind === "unavailable") {
          setState({
            kind: "unavailable",
            uploadHref: `${datasetUploadPath(
              workspace,
              project,
            )}?replace=1&dataset=${encodeURIComponent(dataset)}`,
          });

          return;
        }

        setState({
          kind,
        });
      }
    }

    void loadExplorer();

    return () => {
      controller.abort();
    };
  }, [
    workspace,
    project,
    dataset,
    options,
    estimator,
    onInvalidInterventionDate,
  ]);

  return {
    state,
    quality,
    versions,
    dataset: datasetMetadata,
  };
}

export function useReports(
  workspace: string,
  project: string,
  run: string,
  refreshGeneration = 0,
): LoadState<ReportJob[]> {
  const scopeKey = `${workspace}:${project}:${run}`;

  const [scopedState, setScopedState] = useState<{
    scopeKey: string;
    state: LoadState<ReportJob[]>;
  }>({
    scopeKey,
    state: {
      kind: "loading",
    },
  });

  useEffect(() => {
    const controller = new AbortController();
    const token = localStorage.getItem("incrementality_session_token");
    let pollTimer: ReturnType<typeof setTimeout> | undefined;
    let lastReports: ReportJob[] | null = null;

    if (!token) {
      queueMicrotask(() => {
        if (!controller.signal.aborted) {
          setScopedState({
            scopeKey,
            state: {
              kind: "permission",
            },
          });
        }
      });

      return () => controller.abort();
    }

    const sessionToken: string = token;

    queueMicrotask(() => {
      if (!controller.signal.aborted) {
        setScopedState({
          scopeKey,
          state: {
            kind: "loading",
          },
        });
      }
    });

    async function loadReports(): Promise<void> {
      if (controller.signal.aborted) {
        return;
      }

      try {
        const reports = await fetchReports(
          workspace,
          project,
          run,
          sessionToken,
          controller.signal,
        );

        if (controller.signal.aborted) {
          return;
        }

        lastReports = reports;

        setScopedState({
          scopeKey,
          state: {
            kind: "ready",
            data: reports,
          },
        });

        const hasActiveReport = reports.some(
          (report) =>
            report.status === "pending" || report.status === "running",
        );

        if (hasActiveReport) {
          pollTimer = setTimeout(() => {
            void loadReports();
          }, 3000);
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        const hasActiveReport =
          lastReports?.some(
            (report) =>
              report.status === "pending" || report.status === "running",
          ) ?? false;

        if (hasActiveReport) {
          pollTimer = setTimeout(() => {
            void loadReports();
          }, 3000);

          return;
        }

        setScopedState({
          scopeKey,
          state: {
            kind: failure(error),
          },
        });
      }
    }

    void loadReports();

    return () => {
      controller.abort();

      if (pollTimer !== undefined) {
        clearTimeout(pollTimer);
      }
    };
  }, [workspace, project, run, scopeKey, refreshGeneration]);

  if (scopedState.scopeKey !== scopeKey) {
    return {
      kind: "loading",
    };
  }

  return scopedState.state;
}

export function useDataQuality(
  workspace: string,
  project: string,
  dataset: string,
  estimator: string,
) {
  const [state, setState] = useState<LoadState<DataQuality>>({
    kind: "loading",
  });
  const [datasetMetadata, setDatasetMetadata] =
    useState<Awaited<ReturnType<typeof getDataset>>>();

  useEffect(() => {
    const controller = new AbortController();
    const token = localStorage.getItem("incrementality_session_token");
    let pollTimer: ReturnType<typeof setTimeout> | undefined;

    if (!token) {
      queueMicrotask(() => setState({ kind: "permission" }));
      return;
    }

    const sessionToken: string = token;

    queueMicrotask(() => {
      if (!controller.signal.aborted) {
        setState({ kind: "loading" });
        setDatasetMetadata(undefined);
      }
    });

    async function loadDataset(): Promise<void> {
      if (controller.signal.aborted) {
        return;
      }

      try {
        const datasetRecord = await getDataset(
          sessionToken,
          workspace,
          project,
          dataset,
        );

        if (controller.signal.aborted) {
          return;
        }

        setDatasetMetadata(datasetRecord);

        if (
          datasetRecord.status === "uploaded" ||
          datasetRecord.status === "validating"
        ) {
          pollTimer = setTimeout(() => {
            void loadDataset();
          }, 2000);
          return;
        }

        if (datasetRecord.status !== "ready") {
          return;
        }

        const quality = await assessQuality(
          workspace,
          project,
          dataset,
          estimator,
          sessionToken,
          controller.signal,
        );

        if (!controller.signal.aborted) {
          setState({
            kind: "ready",
            data: quality,
          });
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setState({
            kind: failure(error),
          });
        }
      }
    }

    void loadDataset();

    return () => {
      controller.abort();

      if (pollTimer !== undefined) {
        clearTimeout(pollTimer);
      }
    };
  }, [workspace, project, dataset, estimator]);

  return {
    state,
    dataset: datasetMetadata,
  };
}
