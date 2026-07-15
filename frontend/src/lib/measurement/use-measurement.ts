"use client";

import { useEffect, useState } from "react";

import { fetchChannels, fetchDashboard, MeasurementApiError } from "./api";
import type { ChannelResponse, DashboardFilters, DashboardResponse, LoadState } from "./types";

const failureState = (error: unknown): LoadState<never> => error instanceof MeasurementApiError && [401, 403].includes(error.status) ? { kind: "permission" } : { kind: "error" };

export function useResultsDashboard(workspaceId: string, filters: DashboardFilters): LoadState<DashboardResponse> {
  const [state, setState] = useState<LoadState<DashboardResponse>>({ kind: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    const token = localStorage.getItem("incrementality_session_token");
    if (!token) { queueMicrotask(() => setState({ kind: "permission" })); return; }
    fetchDashboard(workspaceId, filters, token, controller.signal).then((data) => setState({ kind: "ready", data })).catch((error: unknown) => { if (!controller.signal.aborted) setState(failureState(error)); });
    return () => controller.abort();
  }, [workspaceId, filters]);
  return state;
}

export function useChannelPerformance(workspaceId: string): LoadState<ChannelResponse> {
  const [state, setState] = useState<LoadState<ChannelResponse>>({ kind: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    const token = localStorage.getItem("incrementality_session_token");
    if (!token) { queueMicrotask(() => setState({ kind: "permission" })); return; }
    fetchChannels(workspaceId, token, controller.signal).then((data) => setState({ kind: "ready", data })).catch((error: unknown) => { if (!controller.signal.aborted) setState(failureState(error)); });
    return () => controller.abort();
  }, [workspaceId]);
  return state;
}
