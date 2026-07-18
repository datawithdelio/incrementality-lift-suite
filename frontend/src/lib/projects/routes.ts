export function workspacePath(workspaceId: string): string {
  return `/workspaces/${workspaceId}`;
}

export function projectPath(workspaceId: string, projectId: string): string {
  return `${workspacePath(workspaceId)}/projects/${projectId}`;
}

export function datasetUploadPath(
  workspaceId: string,
  projectId: string,
): string {
  return `${projectPath(workspaceId, projectId)}/datasets/upload`;
}
