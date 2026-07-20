"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  SESSION_TOKEN_KEY,
} from "@/lib/auth/api";
import {
  listWorkspaces,
  type AccessibleWorkspace,
} from "@/lib/workspaces/api";

type WorkspaceSettingsState =
  | {
      status: "loading";
    }
  | {
      status: "ready";
      workspace: AccessibleWorkspace;
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

function displayRole(
  role: string,
): string {
  return role
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase()
        + part.slice(1).toLowerCase(),
    )
    .join(" ");
}

export function WorkspaceSettings({
  workspaceId,
}: {
  workspaceId: string;
}) {
  const [
    state,
    setState,
  ] = useState<WorkspaceSettingsState>({
    status: "loading",
  });

  const load = useCallback(
    async () => {
      await Promise.resolve();

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
        const workspaces =
          await listWorkspaces(
            token,
          );

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
              "This workspace is unavailable or you no longer have access.",
          });
          return;
        }

        setState({
          status: "ready",
          workspace,
        });
      } catch {
        setState({
          status: "error",
          message:
            "We couldn't load workspace settings. Please try again.",
        });
      }
    },
    [
      workspaceId,
    ],
  );

  useEffect(() => {
    void Promise
      .resolve()
      .then(load);
  }, [
    load,
  ]);

  if (
    state.status ===
    "loading"
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
            Loading workspace settings…
          </p>
        </div>
      </main>
    );
  }

  if (
    state.status ===
    "error"
  ) {
    return (
      <main className="project-shell">
        <section className="project-state-card">
          <h1>
            Workspace settings unavailable
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
    workspace,
  } = state;

  return (
    <main className="project-shell">
      <header className="workspace-heading">
        <div>
          <p className="project-eyebrow">
            Workspace configuration
          </p>

          <h1>
            Workspace settings
          </h1>

          <p>
            Review the workspace you are currently working in
            and your access level.
          </p>
        </div>
      </header>

      <section
        className="project-section"
        aria-labelledby="workspace-information-heading"
      >
        <div className="project-section-heading">
          <div>
            <h2 id="workspace-information-heading">
              Workspace information
            </h2>

            <p>
              Review the workspace metadata available through your current access.
            </p>
          </div>
        </div>

        <article className="project-details-card">
          <dl>
            <div>
              <dt>
                Workspace name
              </dt>

              <dd>
                {workspace.name}
              </dd>
            </div>

            <div>
              <dt>
                Your role
              </dt>

              <dd>
                {displayRole(
                  workspace.role,
                )}
              </dd>
            </div>

            <div>
              <dt>
                Workspace URL
              </dt>

              <dd>
                {workspace.slug}
              </dd>
            </div>
          </dl>
        </article>

        <div>
          <p>
            Workspace details are currently read-only.
          </p>
          <p>
            The existing workspace API does not support updates.
          </p>
        </div>
      </section>
    </main>
  );
}
