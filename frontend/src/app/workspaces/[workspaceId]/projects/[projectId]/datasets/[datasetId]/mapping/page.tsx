import { SemanticMappingClient } from "@/components/semantic-mapping/semantic-mapping-client";

type SemanticMappingPageProps = {
  params: Promise<{
    workspaceId: string;
    projectId: string;
    datasetId: string;
  }>;
  searchParams?: Promise<{
    estimator?: string;
  }>;
};

export default async function Page({
  params,
  searchParams,
}: SemanticMappingPageProps) {
  const {
    workspaceId,
    projectId,
    datasetId,
  } = await params;
  const query = await searchParams;
  const estimator =
    query?.estimator === "marketing_mix_model"
      ? "marketing_mix_model"
      : undefined;

  return (
    <SemanticMappingClient
      workspaceId={workspaceId}
      projectId={projectId}
      datasetId={datasetId}
      estimator={estimator}
    />
  );
}
