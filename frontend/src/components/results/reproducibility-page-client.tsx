"use client";

import { useAnalysisLineage } from "@/lib/results/use-analysis-lineage";
import { useAnalysisResult } from "@/lib/results/use-analysis-result";

import {
  ReproducibilityExperience,
} from "./reproducibility-experience";

export function ReproducibilityPageClient(
  props: {
    workspaceId: string;
    projectId: string;
    analysisRunId: string;
  },
) {
  const state = useAnalysisLineage(
    props.workspaceId,
    props.projectId,
    props.analysisRunId,
  );

  const analysisState = useAnalysisResult(
    props.workspaceId,
    props.projectId,
    props.analysisRunId,
  );

  const resultAvailable =
    analysisState.kind === "ready"
    && analysisState.data.lifecycle_status === "succeeded"
    && analysisState.data.result !== null;

  return (
    <ReproducibilityExperience
      workspaceId={props.workspaceId}
      projectId={props.projectId}
      analysisRunId={props.analysisRunId}
      resultAvailable={resultAvailable}
      reportsAvailable={resultAvailable}
      state={state}
    />
  );
}
