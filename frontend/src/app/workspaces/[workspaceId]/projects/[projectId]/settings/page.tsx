import {
  ProjectSettings,
} from "@/components/settings/project-settings";

export default async function ProjectSettingsPage({
  params,
}: {
  params: Promise<{
    workspaceId: string;
    projectId: string;
  }>;
}) {
  const {
    workspaceId,
    projectId,
  } = await params;

  return (
    <ProjectSettings
      workspaceId={workspaceId}
      projectId={projectId}
    />
  );
}
