export function workspacePath(workspaceId: string): string {
  return `/workspaces/${workspaceId}`;
}

export function projectPath(workspaceId: string, projectId: string): string {
  return `${workspacePath(workspaceId)}/projects/${projectId}`;
}


export function analysisConfigurationPath(
  workspaceId: string,
  projectId: string,
): string {
  return `${projectPath(workspaceId, projectId)}/analyses/new`;
}



export function analysisRunPath(
  workspaceId: string,
  projectId: string,
  analysisRunId: string,
): string {
  return `${projectPath(
    workspaceId,
    projectId,
  )}/analysis-runs/${analysisRunId}`;
}

export function datasetUploadPath(
  workspaceId: string,
  projectId: string,
): string {
  return `${projectPath(workspaceId, projectId)}/datasets/upload`;
}
