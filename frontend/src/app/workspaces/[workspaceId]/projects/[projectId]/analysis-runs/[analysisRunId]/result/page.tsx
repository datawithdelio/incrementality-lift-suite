import {
  ResultsPageClient,
} from "@/components/results/results-page-client";

export default async function AnalysisResultPage({
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
    <ResultsPageClient
      workspaceId={workspaceId}
      projectId={projectId}
      analysisRunId={analysisRunId}
    />
  );
}
