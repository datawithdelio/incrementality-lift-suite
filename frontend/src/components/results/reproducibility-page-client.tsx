"use client";

import { useAnalysisLineage } from "@/lib/results/use-analysis-lineage";

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

  return (
    <ReproducibilityExperience
      state={state}
    />
  );
}
