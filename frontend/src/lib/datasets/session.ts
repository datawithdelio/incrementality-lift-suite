export function datasetUploadSessionKey(
  workspaceId: string,
  projectId: string,
): string {
  return `incrementality_dataset_upload:${workspaceId}:${projectId}`;
}
