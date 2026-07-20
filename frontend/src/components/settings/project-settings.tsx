"use client";

import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  SESSION_TOKEN_KEY,
} from "@/lib/auth/api";
import {
  getProject,
  type Project,
  ProjectApiError,
  updateProject,
} from "@/lib/projects/api";
import {
  canManageProjects,
} from "@/lib/settings/permissions";
import {
  listWorkspaces,
} from "@/lib/workspaces/api";

type ProjectSettingsState =
  | {
      status: "loading";
    }
  | {
      status: "ready";
      project: Project;
      role: string;
    }
  | {
      status: "error";
      message: string;
    };

function currentToken(): string | null {
  return window.localStorage.getItem(
    SESSION_TOKEN_KEY,
  );
}

function ProjectSettingsScope({
  workspaceId,
  projectId,
}: {
  workspaceId: string;
  projectId: string;
}) {
  const [
    state,
    setState,
  ] = useState<ProjectSettingsState>({
    status: "loading",
  });

  const [
    editing,
    setEditing,
  ] = useState(false);

  const [
    saving,
    setSaving,
  ] = useState(false);

  const [
    saveError,
    setSaveError,
  ] = useState<string | null>(
    null,
  );

  const load = useCallback(
    async () => {
      const token =
        currentToken();

      if (!token) {
        setState({
          status: "error",
          message:
            "Your session is no longer available. Please sign in again.",
        });
        return;
      }

      try {
        const [
          project,
          workspaces,
        ] = await Promise.all([
          getProject(
            token,
            workspaceId,
            projectId,
          ),
          listWorkspaces(
            token,
          ),
        ]);

        const workspace =
          workspaces.find(
            (candidate) =>
              candidate.workspace_id
              === workspaceId,
          );

        if (!workspace) {
          setState({
            status: "error",
            message:
              "This project is unavailable or you no longer have access.",
          });
          return;
        }

        setState({
          status: "ready",
          project,
          role:
            workspace.role,
        });
      } catch (error) {
        setState({
          status: "error",
          message:
            error instanceof ProjectApiError
              ? error.message
              : "We couldn't load project settings. Please try again.",
        });
      }
    },
    [
      projectId,
      workspaceId,
    ],
  );

  useEffect(() => {
    void Promise.resolve().then(
      load,
    );
  }, [
    load,
  ]);

  async function save(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      saving
      || state.status
        !== "ready"
      || !canManageProjects(
        state.role,
      )
    ) {
      return;
    }

    const token =
      currentToken();

    if (!token) {
      setSaveError(
        "Your session is no longer available. Please sign in again.",
      );
      return;
    }

    const values =
      new FormData(
        event.currentTarget,
      );

    const name =
      String(
        values.get("name")
        ?? "",
      ).trim();

    const description =
      String(
        values.get(
          "description",
        ) ?? "",
      ).trim() || null;

    if (!name) {
      setSaveError(
        "Project name is required.",
      );
      return;
    }

    setSaving(true);
    setSaveError(null);

    try {
      const project =
        await updateProject(
          token,
          workspaceId,
          projectId,
          {
            name,
            description,
          },
        );

      setState({
        ...state,
        project,
      });

      setEditing(false);
    } catch (error) {
      setSaveError(
        error instanceof ProjectApiError
          ? error.message
          : "We couldn't update this project. Please try again.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (
    state.status
    === "loading"
  ) {
    return (
      <main className="project-shell">
        <div
          className="project-loading"
          role="status"
        >
          <span />
          <span />
          <span />

          <p>
            Loading project settings…
          </p>
        </div>
      </main>
    );
  }

  if (
    state.status
    === "error"
  ) {
    return (
      <main className="project-shell">
        <section className="project-state-card">
          <h1>
            Project settings unavailable
          </h1>

          <p role="alert">
            {state.message}
          </p>

          <button
            type="button"
            className="project-button project-button-primary"
            onClick={() => {
              setState({
                status:
                  "loading",
              });

              void load();
            }}
          >
            Try again
          </button>
        </section>
      </main>
    );
  }

  const {
    project,
    role,
  } = state;

  const canEdit =
    canManageProjects(
      role,
    );

  return (
    <main className="project-shell">
      <header className="workspace-heading">
        <div>
          <p className="project-eyebrow">
            Project configuration
          </p>

          <h1>
            Project settings
          </h1>

          <p>
            Review and manage the supported details for this project.
          </p>
        </div>

        {canEdit
          && !editing && (
          <button
            type="button"
            className="project-button project-button-secondary"
            onClick={() => {
              setSaveError(null);
              setEditing(true);
            }}
          >
            Edit project
          </button>
        )}
      </header>

      <section
        className="project-section"
        aria-labelledby="project-information-heading"
      >
        <div className="project-section-heading">
          <div>
            <h2 id="project-information-heading">
              Project information
            </h2>

            {!canEdit && (
              <p>
                You have read-only access to project settings.
              </p>
            )}
          </div>
        </div>

        {editing ? (
          <form
            onSubmit={(event) =>
              void save(event)
            }
          >
            <label>
              <span>
                Project name
              </span>

              <input
                aria-label="Project name"
                name="name"
                required
                maxLength={200}
                defaultValue={
                  project.name
                }
              />
            </label>

            <label>
              <span>
                Description
              </span>

              <textarea
                aria-label="Description"
                name="description"
                maxLength={2000}
                rows={4}
                defaultValue={
                  project.description
                  ?? ""
                }
              />
            </label>

            {saveError && (
              <p
                role="alert"
                className="project-form-error"
              >
                {saveError}
              </p>
            )}

            <div>
              <button
                type="button"
                className="project-button project-button-secondary"
                disabled={saving}
                onClick={() => {
                  setSaveError(
                    null,
                  );
                  setEditing(
                    false,
                  );
                }}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="project-button project-button-primary"
                disabled={saving}
              >
                {saving
                  ? "Saving…"
                  : "Save changes"}
              </button>
            </div>
          </form>
        ) : (
          <article className="project-details-card">
            <dl>
              <div>
                <dt>
                  Project name
                </dt>

                <dd>
                  {project.name}
                </dd>
              </div>

              <div>
                <dt>
                  Description
                </dt>

                <dd>
                  {project.description
                    ?? "No description added yet."}
                </dd>
              </div>

              <div>
                <dt>
                  Project URL
                </dt>

                <dd>
                  {project.slug}
                </dd>
              </div>

              <div>
                <dt>
                  Status
                </dt>

                <dd>
                  {project.status
                    === "active"
                    ? "Active"
                    : "Archived"}
                </dd>
              </div>
            </dl>
          </article>
        )}
      </section>
    </main>
  );
}

export function ProjectSettings({
  workspaceId,
  projectId,
}: {
  workspaceId: string;
  projectId: string;
}) {
  return (
    <ProjectSettingsScope
      key={`${workspaceId}:${projectId}`}
      workspaceId={workspaceId}
      projectId={projectId}
    />
  );
}
