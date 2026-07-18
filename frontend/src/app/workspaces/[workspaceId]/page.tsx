import { WorkspaceHome } from "@/components/projects/workspace-home";

export default async function WorkspaceHomePage({
  params,
}: {
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = await params;
  return <WorkspaceHome workspaceId={workspaceId} />;
}
