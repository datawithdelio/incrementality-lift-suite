"use client";

import { useEffect, useState } from "react";

import { fetchAnalysisResult, ResultsApiError } from "./api";
import type { ResultsState } from "./types";

export function useAnalysisResult(
  workspaceId: string,
  projectId: string,
  analysisRunId: string,
): ResultsState {
  const [state, setState] = useState<ResultsState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      const token = window.localStorage.getItem("incrementality_session_token");
      if (!token) {
        setState({ kind: "permission" });
        return;
      }
      try {
        const data = await fetchAnalysisResult(
          workspaceId,
          projectId,
          analysisRunId,
          token,
          controller.signal,
        );
        setState({ kind: "ready", data });
        if (["queued", "running", "retrying"].includes(data.lifecycle_status)) {
          timer = setTimeout(load, 3000);
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof ResultsApiError && [401, 403].includes(error.status)) {
          setState({ kind: "permission" });
        } else if (error instanceof ResultsApiError && error.status === 404) {
          setState({ kind: "missing" });
        } else {
          setState({ kind: "error" });
        }
      }
    };
    void load();
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [workspaceId, projectId, analysisRunId]);
  return state;
}
