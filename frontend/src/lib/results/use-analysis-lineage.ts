"use client";

import { useEffect, useState } from "react";

import {
  fetchAnalysisLineage,
  ResultsApiError,
} from "./api";
import type {
  AnalysisLineageState,
} from "./lineage-types";

export function useAnalysisLineage(
  workspaceId: string,
  projectId: string,
  analysisRunId: string,
): AnalysisLineageState {
  const [state, setState] =
    useState<AnalysisLineageState>({
      kind: "loading",
    });

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      const token = window.localStorage.getItem(
        "incrementality_session_token",
      );

      if (!token) {
        setState({
          kind: "permission",
        });
        return;
      }

      try {
        const data = await fetchAnalysisLineage(
          workspaceId,
          projectId,
          analysisRunId,
          token,
          controller.signal,
        );

        setState({
          kind: "ready",
          data,
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        if (
          error instanceof ResultsApiError &&
          [401, 403].includes(error.status)
        ) {
          setState({
            kind: "permission",
          });
        } else if (
          error instanceof ResultsApiError &&
          error.status === 404
        ) {
          setState({
            kind: "missing",
          });
        } else {
          setState({
            kind: "error",
          });
        }
      }
    }

    void load();

    return () => {
      controller.abort();
    };
  }, [
    workspaceId,
    projectId,
    analysisRunId,
  ]);

  return state;
}
