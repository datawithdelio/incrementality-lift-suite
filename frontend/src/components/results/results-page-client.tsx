"use client";

import { useAnalysisResult } from "@/lib/results/use-analysis-result";

import { ResultsExperience } from "./results-experience";

export function ResultsPageClient(props: {
  workspaceId: string;
  projectId: string;
  analysisRunId: string;
}) {
  const state = useAnalysisResult(props.workspaceId, props.projectId, props.analysisRunId);
  return <ResultsExperience state={state} />;
}
