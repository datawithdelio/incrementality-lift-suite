export function datasetExplorePath(
  workspaceId: string,
  projectId: string,
  datasetId: string,
  estimator?: string,
): string {
  const path = `/workspaces/${workspaceId}/projects/${projectId}/datasets/${datasetId}/explore`;

  return estimator === "marketing_mix_model"
    ? `${path}?estimator=marketing_mix_model`
    : path;
}

export function datasetEstimatorPreferenceKey(datasetId: string): string {
  return `incrementality_dataset_estimator_${datasetId}`;
}

export function datasetQualityPath(
  workspaceId: string,
  projectId: string,
  datasetId: string,
): string {
  return `/workspaces/${workspaceId}/projects/${projectId}/datasets/${datasetId}/quality`;
}

export function datasetMappingPath(
  workspaceId: string,
  projectId: string,
  datasetId: string,
  estimator?: string,
): string {
  const path = `/workspaces/${workspaceId}/projects/${projectId}/datasets/${datasetId}/mapping`;

  return estimator === "marketing_mix_model"
    ? `${path}?estimator=marketing_mix_model`
    : path;
}
