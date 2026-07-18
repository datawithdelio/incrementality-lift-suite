import {
  ReproducibilityPageClient,
} from "@/components/results/reproducibility-page-client";

export default async function AnalysisLineagePage({
  params,
}: {
  params: Promise<{
    workspaceId: string;
    projectId: string;
    analysisRunId: string;
  }>;
}) {
  const {
    workspaceId,
    projectId,
    analysisRunId,
  } = await params;

  return (
    <ReproducibilityPageClient
      workspaceId={workspaceId}
      projectId={projectId}
      analysisRunId={analysisRunId}
    />
  );
}
