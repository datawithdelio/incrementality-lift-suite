export function datasetExplorePath(
  workspaceId: string,
  projectId: string,
  datasetId: string,
): string {
  return `/workspaces/${workspaceId}/projects/${projectId}/datasets/${datasetId}/explore`;
}
