import { SemanticMappingClient } from "@/components/semantic-mapping/semantic-mapping-client";

type SemanticMappingPageProps = {
  params: Promise<{
    workspaceId: string;
    projectId: string;
    datasetId: string;
  }>;
};

export default async function Page({
  params,
}: SemanticMappingPageProps) {
  const {
    workspaceId,
    projectId,
    datasetId,
  } = await params;

  return (
    <SemanticMappingClient
      workspaceId={workspaceId}
      projectId={projectId}
      datasetId={datasetId}
    />
  );
}
