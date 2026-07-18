import type { ReactNode } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/navigation/app-shell";

export default async function WorkspaceLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = await params;

  return (
    <ProtectedRoute>
      <AppShell workspaceId={workspaceId}>
        {children}
      </AppShell>
    </ProtectedRoute>
  );
}
