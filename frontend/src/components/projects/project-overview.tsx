"use client";

import { ArrowRightIcon } from "@phosphor-icons/react/ArrowRight";
import { WarningCircleIcon } from "@phosphor-icons/react/WarningCircle";
import { XIcon } from "@phosphor-icons/react/X";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { SESSION_TOKEN_KEY } from "@/lib/auth/api";
import {
  datasetExplorePath,
  datasetMappingPath,
  datasetQualityPath,
} from "@/lib/datasets/routes";
import {
  getProjectOverview,
  listProjects,
  type Project,
  type ProjectOverview as ProjectOverviewData,
  ProjectApiError,
  updateProject,
} from "@/lib/projects/api";
import {
  datasetUploadPath,
  projectPath,
  workspacePath,
} from "@/lib/projects/routes";
import { projectNextAction } from "@/lib/projects/next-action";

type OverviewState =
  | { status: "loading" }
  | { status: "ready"; project: ProjectOverviewData; projects: Project[] }
  | { status: "error"; message: string };

function currentToken(): string | null {
  return window.localStorage.getItem(SESSION_TOKEN_KEY);
}

export function ProjectOverview({
  workspaceId,
  projectId,
}: {
  workspaceId: string;
  projectId: string;
}) {
  const router = useRouter();
  const [state, setState] = useState<OverviewState>({ status: "loading" });
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const load = useCallback(async () => {
    await Promise.resolve();
    const token = currentToken();
    if (!token) {
      setState({ status: "error", message: "Your session is no longer available. Please sign in again." });
      return;
    }

    try {
      const [project, projects] = await Promise.all([
        getProjectOverview(token, workspaceId, projectId),
        listProjects(token, workspaceId),
      ]);
      setState({ status: "ready", project, projects });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof ProjectApiError
          ? error.message
          : "We couldn't load this project. Please try again.",
      });
    }
  }, [projectId, workspaceId]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || state.status !== "ready") return;
    const token = currentToken();
    if (!token) {
      setSaveError("Your session is no longer available. Please sign in again.");
      return;
    }

    const values = new FormData(event.currentTarget);
    setSaving(true);
    setSaveError(null);
    try {
      const project = await updateProject(token, workspaceId, projectId, {
        name: String(values.get("name") ?? "").trim(),
        description: String(values.get("description") ?? "").trim() || null,
      });
      setState({
        ...state,
        project: { ...state.project, ...project },
      });
      setEditing(false);
      toast.success("Project updated", {
        description: "The project name and description are now up to date.",
      });
    } catch (error) {
      const message = error instanceof ProjectApiError
        ? error.message
        : "We couldn't update this project. Please try again.";
      setSaveError(message);
      toast.error("Changes not saved", { description: message });
    } finally {
      setSaving(false);
    }
  }

  if (state.status === "loading") {
    return <main className="project-shell"><div className="project-loading" role="status"><span /><span /><span /><p>Loading project overview…</p></div></main>;
  }

  if (state.status === "error") {
    return (
      <main className="project-shell"><section className="project-state-card">
        <span className="project-state-mark" aria-hidden="true"><WarningCircleIcon size={24} weight="duotone" /></span>
        <h1>Project unavailable</h1><p role="alert">{state.message}</p>
        <div className="project-state-actions"><button type="button" className="project-button project-button-primary" onClick={() => { setState({ status: "loading" }); void load(); }}>Try again</button><Link href={workspacePath(workspaceId)}>Back to projects</Link></div>
      </section></main>
    );
  }

  const { project, projects } = state;
  const nextAction = projectNextAction(project);

  const datasetActionHref = project.latest_dataset_id
    ? project.latest_dataset_status === "ready"
      && !project.semantic_mapping_configured
      ? datasetMappingPath(
          workspaceId,
          projectId,
          project.latest_dataset_id,
        )
      : datasetExplorePath(
          workspaceId,
          projectId,
          project.latest_dataset_id,
        )
    : null;

  const actionHref =
    nextAction.destination === "dataset"
      ? datasetActionHref
      : nextAction.destination === "analysis"
        && project.latest_analysis_run_id
        ? `/workspaces/${workspaceId}/projects/${projectId}/analysis-runs/${project.latest_analysis_run_id}`
        : null;
  return (
    <main className="project-shell project-overview">
      <nav className="project-breadcrumb" aria-label="Breadcrumb"><Link href={workspacePath(workspaceId)}>Projects</Link><span aria-hidden="true">/</span><span>{project.name}</span></nav>
      <header className="project-overview-heading">
        <div><p className="project-eyebrow">Active project</p><h1>{project.name}</h1><p>{project.description ?? "No description added yet."}</p></div>
        <div className="project-overview-actions">
          <label><span>Switch project</span><select aria-label="Switch project" value={project.id} onChange={(event) => router.push(projectPath(workspaceId, event.target.value))}>{projects.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></label>
          <button type="button" className="project-button project-button-secondary" onClick={() => setEditing(true)}>Edit project</button>
        </div>
      </header>

      <section className="project-overview-grid">
        <article className="project-primary-card">
          <p className="project-eyebrow">Recommended next step</p>
          <h2>{nextAction.title}</h2>
          <p>{nextAction.description}</p>
          {actionHref ? (
            <Link className="project-next-link" href={actionHref}>Open current step <ArrowRightIcon size={16} aria-hidden="true" /></Link>
          ) : (
            <span className="project-muted-action" aria-disabled="true">This next workflow is not part of the project-lifecycle release</span>
          )}
        </article>
        {!project.latest_dataset_id && (
          <article className="project-details-card" aria-labelledby="project-data-heading">
            <h2 id="project-data-heading">Data</h2>
            <p><strong>No dataset uploaded</strong></p>
            <p>Upload a dataset to begin configuring your analysis.</p>
            <Link
              className="project-next-link"
              href={datasetUploadPath(workspaceId, projectId)}
            >
              Upload Dataset
              <ArrowRightIcon size={16} aria-hidden="true" />
            </Link>
          </article>
        )}

        {project.latest_dataset_id
          && project.latest_dataset_status === "pending_upload" && (
          <article
            className="project-details-card"
            aria-labelledby="project-data-pending-heading"
          >
            <h2 id="project-data-pending-heading">Data</h2>
            <p><strong>Upload pending</strong></p>
            <p>
              The dataset was registered, but its file upload has not completed.
            </p>
            <Link
              className="project-next-link"
              href={datasetUploadPath(workspaceId, projectId)}
            >
              Resume Upload
              <ArrowRightIcon size={16} aria-hidden="true" />
            </Link>
          </article>
        )}

        {project.latest_dataset_id
          && project.latest_dataset_status === "uploaded" && (
          <article
            className="project-details-card"
            aria-labelledby="project-data-uploaded-heading"
          >
            <h2 id="project-data-uploaded-heading">Data</h2>
            <p><strong>Validation pending</strong></p>
            <p>
              Your dataset upload is complete and is waiting for backend validation.
            </p>
            <Link
              className="project-next-link"
              href={datasetUploadPath(workspaceId, projectId)}
            >
              View Status
              <ArrowRightIcon size={16} aria-hidden="true" />
            </Link>
          </article>
        )}

        {project.latest_dataset_id
          && project.latest_dataset_status === "validating" && (
          <article
            className="project-details-card"
            aria-labelledby="project-data-validating-heading"
          >
            <h2 id="project-data-validating-heading">Data</h2>
            <p><strong>Validation in progress</strong></p>
            <p>
              Your dataset is being validated by the backend.
            </p>
            <Link
              className="project-next-link"
              href={datasetUploadPath(workspaceId, projectId)}
            >
              View Status
              <ArrowRightIcon size={16} aria-hidden="true" />
            </Link>
          </article>
        )}

        {project.latest_dataset_id
          && project.latest_dataset_status === "failed" && (
          <article
            className="project-details-card"
            aria-labelledby="project-data-failed-heading"
          >
            <h2 id="project-data-failed-heading">Data</h2>
            <p><strong>Dataset validation failed</strong></p>
            <p>
              Review the validation failure and upload a corrected dataset when ready.
            </p>
            <Link
              className="project-next-link"
              href={datasetUploadPath(workspaceId, projectId)}
            >
              Review Failure
              <ArrowRightIcon size={16} aria-hidden="true" />
            </Link>
          </article>
        )}

        {project.latest_dataset_id
          && project.latest_dataset_status === "ready" && (
          <article
            className="project-details-card"
            aria-labelledby="project-data-ready-heading"
          >
            <h2 id="project-data-ready-heading">Data</h2>
            <p><strong>Dataset ready</strong></p>
            <p>
              Your dataset passed validation and is ready to explore.
            </p>
            <Link
              className="project-next-link"
              href={datasetExplorePath(
                workspaceId,
                projectId,
                project.latest_dataset_id,
              )}
            >
              Explore Dataset
              <ArrowRightIcon size={16} aria-hidden="true" />
            </Link>
              {project.semantic_mapping_configured && (
                <Link
                  className="project-next-link"
                  href={datasetMappingPath(
                    workspaceId,
                    projectId,
                    project.latest_dataset_id,
                  )}
                >
                  View/Edit Mapping
                  <ArrowRightIcon size={16} aria-hidden="true" />
                </Link>
              )}
              <Link
                className="project-next-link"
                href={datasetQualityPath(
                  workspaceId,
                  projectId,
                  project.latest_dataset_id,
                )}
              >
                View Data Quality
                <ArrowRightIcon size={16} aria-hidden="true" />
              </Link>
          </article>
        )}

        <article className="project-details-card">
          <h2>Project details</h2>
          <dl><div><dt>Status</dt><dd>Active</dd></div><div><dt>Project URL</dt><dd>{project.slug}</dd></div><div><dt>Created</dt><dd>{new Date(project.created_at).toLocaleDateString()}</dd></div></dl>
        </article>
      </section>

      <section className="project-journey" aria-labelledby="journey-heading">
        <div><p className="project-eyebrow">Measurement workflow</p><h2 id="journey-heading">Build evidence in clear stages</h2></div>
        <ol><li className={nextAction.stage === 1 ? "is-current" : "is-complete"}><span>01</span><div><strong>Project</strong><small>Ready</small></div></li><li className={nextAction.stage === 2 ? "is-current" : nextAction.stage > 2 ? "is-complete" : undefined}><span>02</span><div><strong>Data</strong><small>{project.latest_dataset_status ?? "Not connected"}</small></div></li><li className={nextAction.stage === 3 ? "is-current" : nextAction.stage > 3 ? "is-complete" : undefined}><span>03</span><div><strong>Analysis</strong><small>{project.latest_analysis_run_status ?? "Not started"}</small></div></li><li className={nextAction.stage === 4 ? "is-current" : undefined}><span>04</span><div><strong>Decision</strong><small>Results and reports</small></div></li></ol>
      </section>

      {editing && (
        <div className="project-dialog-backdrop" role="presentation" onMouseDown={() => !saving && setEditing(false)}><section className="project-dialog" role="dialog" aria-modal="true" aria-labelledby="edit-project-heading" onMouseDown={(event) => event.stopPropagation()}>
          <div className="project-dialog-heading"><div><p className="project-eyebrow">Project settings</p><h2 id="edit-project-heading">Edit project</h2></div><button type="button" aria-label="Close project form" disabled={saving} onClick={() => setEditing(false)}><XIcon size={17} aria-hidden="true" /></button></div>
          <form onSubmit={(event) => void save(event)}>
            <label><span>Project name</span><input aria-label="Project name" name="name" required maxLength={200} defaultValue={project.name} /></label>
            <label><span>Description</span><textarea aria-label="Description" name="description" maxLength={2000} rows={4} defaultValue={project.description ?? ""} /></label>
            <p className="project-slug-note">The stable project URL <strong>{project.slug}</strong> will not change.</p>
            {saveError && <p className="project-form-error" role="alert">{saveError}</p>}
            <footer><button type="button" className="project-button project-button-secondary" disabled={saving} onClick={() => setEditing(false)}>Cancel</button><button type="submit" className="project-button project-button-primary" disabled={saving}>{saving ? "Saving…" : "Save changes"}</button></footer>
          </form>
        </section></div>
      )}
    </main>
  );
}
