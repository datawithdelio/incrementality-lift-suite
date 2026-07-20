import {
  WorkspaceSettings,
} from "@/components/settings/workspace-settings";

export default async function WorkspaceSettingsPage({
  params,
}: {
  params: Promise<{
    workspaceId: string;
  }>;
}) {
  const {
    workspaceId,
  } = await params;

  return (
    <WorkspaceSettings
      workspaceId={workspaceId}
    />
  );
}
