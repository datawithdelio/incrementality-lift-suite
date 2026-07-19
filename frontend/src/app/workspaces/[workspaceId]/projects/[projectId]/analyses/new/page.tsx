import { AnalysisConfigurationClient } from "@/components/analysis-configuration/analysis-configuration-client";

type AnalysisConfigurationPageProps = {
  params: Promise<{
    workspaceId: string;
    projectId: string;
  }>;
};

export default async function Page({
  params,
}: AnalysisConfigurationPageProps) {
  const {
    workspaceId,
    projectId,
  } = await params;

  return (
    <AnalysisConfigurationClient
      workspaceId={workspaceId}
      projectId={projectId}
    />
  );
}
