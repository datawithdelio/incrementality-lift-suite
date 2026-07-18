import { ProjectOverview } from "@/components/projects/project-overview";

export default async function ProjectOverviewPage({
  params,
}: {
  params: Promise<{ workspaceId: string; projectId: string }>;
}) {
  const { workspaceId, projectId } = await params;
  return (
    <ProjectOverview
      key={`${workspaceId}:${projectId}`}
      workspaceId={workspaceId}
      projectId={projectId}
    />
  );
}
