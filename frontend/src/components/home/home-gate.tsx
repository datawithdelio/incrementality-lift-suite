"use client";

import type { ReactNode } from "react";

import { useAuth } from "../auth/auth-provider";
import { WorkspaceBootstrap } from "../workspaces/workspace-bootstrap";

export function HomeGate({
  children,
}: {
  children: ReactNode;
}) {
  const auth = useAuth();

  if (auth.status === "checking") {
    return (
      <div
        role="status"
        aria-live="polite"
      >
        Checking your session…
      </div>
    );
  }

  if (auth.status === "authenticated") {
    return <WorkspaceBootstrap />;
  }

  return children;
}
