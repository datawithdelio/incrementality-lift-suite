"use client";

import { useState } from "react";

import { useAnalysisResult } from "@/lib/results/use-analysis-result";

import { ResultsExperience } from "./results-experience";

export function ResultsPageClient(props: {
  workspaceId: string;
  projectId: string;
  analysisRunId: string;
}) {
  const [
    retryKey,
    setRetryKey,
  ] = useState(0);

  const state = useAnalysisResult(
    props.workspaceId,
    props.projectId,
    props.analysisRunId,
    retryKey,
  );

  return (
    <ResultsExperience
      state={state}
      onRetry={() => {
        setRetryKey(
          (current) =>
            current + 1,
        );
      }}
    />
  );
}
