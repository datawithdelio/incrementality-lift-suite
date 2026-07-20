"use client";

import { ArrowRightIcon } from "@phosphor-icons/react/ArrowRight";
import { FolderPlusIcon } from "@phosphor-icons/react/FolderPlus";
import { PlusIcon } from "@phosphor-icons/react/Plus";
import { WarningCircleIcon } from "@phosphor-icons/react/WarningCircle";
import { XIcon } from "@phosphor-icons/react/X";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { SESSION_TOKEN_KEY } from "@/lib/auth/api";
import {
  createProject,
  listProjects,
  type Project,
  ProjectApiError,
} from "@/lib/projects/api";
import { projectPath } from "@/lib/projects/routes";
import {
  canManageProjects,
} from "@/lib/settings/permissions";
import { listWorkspaces, type AccessibleWorkspace } from "@/lib/workspaces/api";

type WorkspaceHomeState =
  | { status: "loading" }
  | { status: "ready"; workspace: AccessibleWorkspace; projects: Project[] }
  | { status: "error"; message: string };

function displayRole(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1).toLowerCase();
}

function projectDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function currentToken(): string | null {
  return window.localStorage.getItem(SESSION_TOKEN_KEY);
}

export function WorkspaceHome({ workspaceId }: { workspaceId: string }) {
  const router = useRouter();
  const [state, setState] = useState<WorkspaceHomeState>({ status: "loading" });
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(async () => {
    await Promise.resolve();
    const token = currentToken();
    if (!token) {
      setState({ status: "error", message: "Your session is no longer available. Please sign in again." });
      return;
    }

    try {
      const [workspaces, projects] = await Promise.all([
        listWorkspaces(token),
        listProjects(token, workspaceId),
      ]);
      const workspace = workspaces.find((candidate) => candidate.workspace_id === workspaceId);
      if (!workspace) {
        setState({ status: "error", message: "This workspace is unavailable or you no longer have access." });
        return;
      }
      setState({ status: "ready", workspace, projects });
    } catch {
      setState({ status: "error", message: "We couldn't load this workspace. Please try again." });
    }
  }, [workspaceId]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  async function submitProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (
      creating
      || state.status !== "ready"
      || !canManageProjects(
        state.workspace.role,
      )
    ) {
      return;
    }

    const token = currentToken();
    if (!token) {
      setCreateError("Your session is no longer available. Please sign in again.");
      return;
    }

    const values = new FormData(event.currentTarget);
    const input = {
      name: String(values.get("name") ?? "").trim(),
      slug: String(values.get("slug") ?? "").trim().toLowerCase(),
      description: String(values.get("description") ?? "").trim() || null,
    };

    setCreating(true);
    setCreateError(null);
    try {
      const project = await createProject(token, workspaceId, input);
      toast.success("Project created", {
        description: `${project.name} is ready for data and analysis.`,
      });
      router.push(projectPath(workspaceId, project.id));
    } catch (error) {
      const message = error instanceof ProjectApiError
        ? error.message
        : "We couldn't create this project. Please try again.";
      setCreateError(message);
      toast.error("Project not created", { description: message });
    } finally {
      setCreating(false);
    }
  }

  if (state.status === "loading") {
    return <main className="project-shell"><div className="project-loading" role="status"><span /><span /><span /><p>Loading workspace projects…</p></div></main>;
  }

  if (state.status === "error") {
    return (
      <main className="project-shell">
        <section className="project-state-card">
          <span className="project-state-mark" aria-hidden="true"><WarningCircleIcon size={24} weight="duotone" /></span>
          <h1>Workspace unavailable</h1>
          <p role="alert">{state.message}</p>
          <button type="button" className="project-button project-button-primary" onClick={() => { setState({ status: "loading" }); void load(); }}>Try again</button>
        </section>
      </main>
    );
  }

  const canCreateProject =
    canManageProjects(
      state.workspace.role,
    );

  return (
    <main className="project-shell">
      <header className="workspace-heading">
        <div>
          <p className="project-eyebrow">Workspace · <span>{displayRole(state.workspace.role)}</span></p>
          <h1>{state.workspace.name}</h1>
          <p>Organize datasets, analysis runs, and decision-ready results by project.</p>
        </div>
        {canCreateProject && (
          <button type="button" className="project-button project-button-primary" onClick={() => setCreateOpen(true)}>
            <PlusIcon size={17} weight="bold" aria-hidden="true" /> New project
          </button>
        )}
      </header>

      <section className="project-section" aria-labelledby="projects-heading">
        <div className="project-section-heading">
          <div><h2 id="projects-heading">Projects</h2><p>{state.projects.length} active</p></div>
        </div>

        {state.projects.length === 0 ? (
          <div className="project-empty">
            <span aria-hidden="true"><FolderPlusIcon size={24} weight="duotone" /></span>
            <h3>No projects yet</h3>
            <p>Create a project to give your first measurement workflow a stable home.</p>
            {canCreateProject && (
              <button type="button" className="project-button project-button-primary" onClick={() => setCreateOpen(true)}>Create your first project</button>
            )}
          </div>
        ) : (
          <div className="project-grid">
            {state.projects.map((project) => (
              <Link key={project.id} href={projectPath(workspaceId, project.id)} className="project-card">
                <span className="project-card-mark" aria-hidden="true">{project.name.slice(0, 2).toUpperCase()}</span>
                <div className="project-card-copy">
                  <div><h3>{project.name}</h3><span className="project-status">Active</span></div>
                  <p>{project.description ?? "No description added yet."}</p>
                  <small>Created {projectDate(project.created_at)}</small>
                </div>
                <span className="project-card-arrow" aria-hidden="true"><ArrowRightIcon size={18} /></span>
              </Link>
            ))}
          </div>
        )}
      </section>

      {canCreateProject && createOpen && (
        <div className="project-dialog-backdrop" role="presentation" onMouseDown={() => !creating && setCreateOpen(false)}>
          <section className="project-dialog" role="dialog" aria-modal="true" aria-labelledby="create-project-heading" onMouseDown={(event) => event.stopPropagation()}>
            <div className="project-dialog-heading">
              <div><p className="project-eyebrow">New measurement space</p><h2 id="create-project-heading">Create project</h2></div>
              <button type="button" aria-label="Close project form" disabled={creating} onClick={() => setCreateOpen(false)}><XIcon size={17} aria-hidden="true" /></button>
            </div>
            <form onSubmit={(event) => void submitProject(event)}>
              <label><span>Project name</span><input aria-label="Project name" name="name" required maxLength={200} autoFocus placeholder="Paid Search Lift" /></label>
              <label><span>Project URL</span><input aria-label="Project URL" name="slug" required maxLength={100} pattern="[a-z0-9]+(?:-[a-z0-9]+)*" placeholder="paid-search-lift" /><small>Lowercase letters, numbers, and hyphens.</small></label>
              <label><span>Description</span><textarea aria-label="Description" name="description" maxLength={2000} rows={4} placeholder="What decision will this project support?" /></label>
              {createError && <p className="project-form-error" role="alert">{createError}</p>}
              <footer><button type="button" className="project-button project-button-secondary" disabled={creating} onClick={() => setCreateOpen(false)}>Cancel</button><button type="submit" className="project-button project-button-primary" disabled={creating}>{creating ? "Creating…" : "Create project"}</button></footer>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}
