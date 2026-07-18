"use client";
import { useEffect, useState } from "react";
import { getDataset } from "../datasets/api";
import { assessQuality, DataProductApiError, ExplorerOptions, fetchDatasetVersions, fetchPreview, fetchReports } from "./api";
import type { DataQuality, DatasetPreview, DatasetVersion, LoadState, ReportJob } from "./types";
const failure = (error: unknown): "permission" | "error" => error instanceof DataProductApiError && [401, 403].includes(error.status) ? "permission" : "error";
export function useDatasetExplorer(workspace: string, project: string, dataset: string, options: ExplorerOptions, estimator: string) { const [state, setState] = useState<LoadState<DatasetPreview>>({ kind: "loading" }); const [quality, setQuality] = useState<DataQuality>(); const [versions, setVersions] = useState<DatasetVersion[]>([]); const [datasetMetadata, setDatasetMetadata] = useState<Awaited<ReturnType<typeof getDataset>>>(); useEffect(() => { const controller = new AbortController(); const token = localStorage.getItem("incrementality_session_token"); if (!token) { queueMicrotask(() => setState({ kind: "permission" })); return; } queueMicrotask(() => { if (!controller.signal.aborted) setState({ kind: "loading" }); }); Promise.all([fetchPreview(workspace, project, dataset, options, token, controller.signal), assessQuality(workspace, project, dataset, estimator, token, controller.signal), fetchDatasetVersions(workspace, project, token, controller.signal), getDataset(token, workspace, project, dataset)]).then(([data, assessment, datasetVersions, datasetRecord]) => { setState({ kind: "ready", data }); setQuality(assessment); setVersions(datasetVersions); setDatasetMetadata(datasetRecord); }).catch((error) => { if (!controller.signal.aborted) setState({ kind: failure(error) }); }); return () => controller.abort(); }, [workspace, project, dataset, options, estimator]); return { state, quality, versions, dataset: datasetMetadata }; }
export function useReports(workspace: string, project: string, run: string) { const [reports, setReports] = useState<ReportJob[]>([]); useEffect(() => { const controller = new AbortController(); const token = localStorage.getItem("incrementality_session_token"); if (token) fetchReports(workspace, project, run, token, controller.signal).then(setReports).catch(() => undefined); return () => controller.abort(); }, [workspace, project, run]); return reports; }

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
    const token = localStorage.getItem(
      "incrementality_session_token",
    );
    let pollTimer: ReturnType<typeof setTimeout> | undefined;

    if (!token) {
      queueMicrotask(() =>
        setState({ kind: "permission" }),
      );
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
  }, [
    workspace,
    project,
    dataset,
    estimator,
  ]);

  return {
    state,
    dataset: datasetMetadata,
  };
}
