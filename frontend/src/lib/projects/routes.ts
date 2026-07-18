export function workspacePath(workspaceId: string): string {
  return `/workspaces/${workspaceId}`;
}

export function projectPath(workspaceId: string, projectId: string): string {
  return `${workspacePath(workspaceId)}/projects/${projectId}`;
}
