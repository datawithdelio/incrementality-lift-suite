"use client";

import { useState } from "react";

import type { DashboardFilters } from "@/lib/measurement/types";
import { useChannelPerformance, useResultsDashboard } from "@/lib/measurement/use-measurement";

import { ChannelPerformance } from "./channel-performance";
import { ResultsDashboard } from "./results-dashboard";

export function DashboardClient({ workspaceId }: { workspaceId: string }) {
  const [filters, setFilters] = useState<DashboardFilters>({});
  const state = useResultsDashboard(workspaceId, filters);
  return <main className="results-shell">
    <Header title="Measurement program" subtitle="A method-aware view of lift, reliability, and business impact." />
    <div className="filters">
      <input aria-label="Project ID" placeholder="Filter by project ID" onChange={(event) => setFilters({ ...filters, projectId: event.target.value || undefined })} />
      <select aria-label="Estimator" onChange={(event) => setFilters({ ...filters, estimator: event.target.value || undefined })}>
        <option value="">All methods</option><option value="difference_in_differences">Difference in Differences</option><option value="synthetic_control">Synthetic Control</option><option value="geo_holdout">Geo Holdout</option><option value="marketing_mix_model">Marketing Mix Modeling</option><option value="off_policy_evaluation">Off-Policy Evaluation</option>
      </select>
      <select aria-label="Status" onChange={(event) => setFilters({ ...filters, status: event.target.value || undefined })}>
        <option value="">All statuses</option><option value="running">Running</option><option value="succeeded">Succeeded</option><option value="failed">Failed</option>
      </select>
      <input aria-label="Start date" type="date" onChange={(event) => setFilters({ ...filters, dateFrom: event.target.value || undefined })} />
      <input aria-label="End date" type="date" onChange={(event) => setFilters({ ...filters, dateTo: event.target.value || undefined })} />
    </div>
    <ResultsDashboard state={state} workspaceId={workspaceId} />
  </main>;
}

export function ChannelClient({ workspaceId }: { workspaceId: string }) {
  return <main className="results-shell"><Header title="Channel performance" subtitle="Budget guidance based on incremental evidence—not raw conversion correlation." /><ChannelPerformance state={useChannelPerformance(workspaceId)} /></main>;
}

function Header({ title, subtitle }: { title: string; subtitle: string }) {
  return <header className="measurement-hero"><p className="eyebrow">Decision workspace</p><h1>{title}</h1><p>{subtitle}</p></header>;
}
