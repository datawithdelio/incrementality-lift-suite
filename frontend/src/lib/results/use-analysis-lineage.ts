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
  const requestKey =
    `${workspaceId}:${projectId}:${analysisRunId}`;

  const [
    storedState,
    setStoredState,
  ] = useState<{
    requestKey: string;
    state: AnalysisLineageState;
  }>({
    requestKey,
    state: {
      kind: "loading",
    },
  });

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      const token = window.localStorage.getItem(
        "incrementality_session_token",
      );

      if (!token) {
        setStoredState({
          requestKey,
          state: {
            kind: "permission",
          },
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

        setStoredState({
          requestKey,
          state: {
            kind: "ready",
            data,
          },
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        if (
          error instanceof ResultsApiError &&
          [401, 403].includes(error.status)
        ) {
          setStoredState({
            requestKey,
            state: {
              kind: "permission",
            },
          });
        } else if (
          error instanceof ResultsApiError &&
          error.status === 404
        ) {
          setStoredState({
            requestKey,
            state: {
              kind: "missing",
            },
          });
        } else {
          setStoredState({
            requestKey,
            state: {
              kind: "error",
            },
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
    requestKey,
  ]);

  if (
    storedState.requestKey
    !== requestKey
  ) {
    return {
      kind: "loading",
    };
  }

  return storedState.state;
}
