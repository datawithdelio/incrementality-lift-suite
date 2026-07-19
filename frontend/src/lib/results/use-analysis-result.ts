"use client";

import { useEffect, useState } from "react";

import { fetchAnalysisResult, ResultsApiError } from "./api";
import type { ResultsState } from "./types";

export function useAnalysisResult(
  workspaceId: string,
  projectId: string,
  analysisRunId: string,
  retryKey = 0,
): ResultsState {
  const requestKey =
    `${workspaceId}:${projectId}:${analysisRunId}`;

  const [
    storedState,
    setStoredState,
  ] = useState<{
    requestKey: string;
    state: ResultsState;
  }>({
    requestKey,
    state: {
      kind: "loading",
    },
  });

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let lastKnownData:
      | Extract<ResultsState, { kind: "ready" }>["data"]
      | undefined;

    const isNonTerminal = (
      status: string,
    ) =>
      [
        "queued",
        "running",
        "retrying",
      ].includes(status);

    const load = async () => {
      const token = window.localStorage.getItem("incrementality_session_token");
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
        const data = await fetchAnalysisResult(
          workspaceId,
          projectId,
          analysisRunId,
          token,
          controller.signal,
        );
        lastKnownData = data;
        setStoredState({
          requestKey,
          state: {
            kind: "ready",
            data,
            refreshError: false,
          },
        });

        if (
          isNonTerminal(
            data.lifecycle_status,
          )
        ) {
          timer = setTimeout(
            load,
            3000,
          );
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof ResultsApiError && [401, 403].includes(error.status)) {
          setStoredState({
          requestKey,
          state: {
            kind: "permission",
          },
        });
        } else if (error instanceof ResultsApiError && error.status === 404) {
          setStoredState({
            requestKey,
            state: {
              kind: "missing",
            },
          });
        } else if (
          lastKnownData
          && isNonTerminal(
            lastKnownData
              .lifecycle_status,
          )
        ) {
          setStoredState({
            requestKey,
            state: {
              kind: "ready",
              data: lastKnownData,
              refreshError: true,
            },
          });

          timer = setTimeout(
            load,
            3000,
          );
        } else {
          setStoredState({
            requestKey,
            state: {
              kind: "error",
            },
          });
        }
      }
    };
    void load();
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [
    workspaceId,
    projectId,
    analysisRunId,
    requestKey,
    retryKey,
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
