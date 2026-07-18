import { DataQualityClient } from "@/components/data-products/data-quality-client";

type DataQualityPageProps = {
  params: Promise<{
    workspaceId: string;
    projectId: string;
    datasetId: string;
  }>;
};

export default async function Page({
  params,
}: DataQualityPageProps) {
  const {
    workspaceId,
    projectId,
    datasetId,
  } = await params;

  return (
    <DataQualityClient
      workspaceId={workspaceId}
      projectId={projectId}
      datasetId={datasetId}
    />
  );
}
