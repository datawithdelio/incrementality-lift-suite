"use client";

import {
  useAnalysisResult,
} from "@/lib/results/use-analysis-result";

import {
  AnalysisRunStatusExperience,
} from "./analysis-run-status-experience";

export function AnalysisRunStatusPageClient({
  workspaceId,
  projectId,
  analysisRunId,
}: {
  workspaceId: string;
  projectId: string;
  analysisRunId: string;
}) {
  const state =
    useAnalysisResult(
      workspaceId,
      projectId,
      analysisRunId,
    );

  return (
    <AnalysisRunStatusExperience
      state={state}
    />
  );
}
