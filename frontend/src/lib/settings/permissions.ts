export type WorkspaceRole =
  | "owner"
  | "admin"
  | "analyst"
  | "viewer";

function isWorkspaceRole(
  role: string,
): role is WorkspaceRole {
  return (
    role === "owner"
    || role === "admin"
    || role === "analyst"
    || role === "viewer"
  );
}

export function canManageWorkspace(
  role: string,
): boolean {
  if (!isWorkspaceRole(role)) {
    return false;
  }

  return (
    role === "owner"
    || role === "admin"
  );
}

export function canManageMembers(
  role: string,
): boolean {
  if (!isWorkspaceRole(role)) {
    return false;
  }

  return (
    role === "owner"
    || role === "admin"
  );
}

export function canManageProjects(
  role: string,
): boolean {
  if (!isWorkspaceRole(role)) {
    return false;
  }

  return (
    role === "owner"
    || role === "admin"
    || role === "analyst"
  );
}
