import {
  MembersAccess,
} from "@/components/settings/members-access";

export default async function MembersAccessPage({
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
    <MembersAccess
      workspaceId={workspaceId}
    />
  );
}
