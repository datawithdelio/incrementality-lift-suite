import { DatasetUpload } from "@/components/datasets/dataset-upload";

type UploadDatasetPageProps = {
  params: Promise<{
    workspaceId: string;
    projectId: string;
  }>;
};

export default async function UploadDatasetPage({
  params,
}: UploadDatasetPageProps) {
  const {
    workspaceId,
    projectId,
  } = await params;

  return (
    <main className="project-shell">
      <DatasetUpload
        workspaceId={workspaceId}
        projectId={projectId}
      />
    </main>
  );
}
