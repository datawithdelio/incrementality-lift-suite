"use client";

import { useRouter } from "next/navigation";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import { useAuth } from "../auth/auth-provider";
import {
  SESSION_TOKEN_KEY,
  WORKSPACE_ID_KEY,
} from "../../lib/auth/api";
import {
  type AccessibleWorkspace,
  createWorkspace,
  listWorkspaces,
} from "../../lib/workspaces/api";

type BootstrapState =
  | { status: "loading" }
  | { status: "onboarding" }
  | {
      status: "selecting";
      workspaces: AccessibleWorkspace[];
    }
  | {
      status: "error";
      message: string;
    };

export function WorkspaceBootstrap() {
  const router = useRouter();
  const auth = useAuth();

  const [state, setState] =
    useState<BootstrapState>({
      status: "loading",
    });

  const [creating, setCreating] =
    useState(false);

  const [creationError, setCreationError] =
    useState<string | null>(null);

  const enterWorkspace = useCallback(
    (workspaceId: string) => {
      window.localStorage.setItem(
        WORKSPACE_ID_KEY,
        workspaceId,
      );

      router.push(
        `/workspaces/${workspaceId}/results-dashboard`,
      );
    },
    [router],
  );

  const loadAccessibleWorkspaces =
    useCallback(async () => {
      const token =
        window.localStorage.getItem(
          SESSION_TOKEN_KEY,
        );

      if (!token) {
        await Promise.resolve();

        setState({
          status: "error",
          message:
            "We couldn't load your workspaces. Please sign in again.",
        });
        return;
      }

      try {
        const workspaces =
          await listWorkspaces(token);

        if (workspaces.length === 0) {
          setState({
            status: "onboarding",
          });
          return;
        }

        if (workspaces.length === 1) {
          enterWorkspace(
            workspaces[0].workspace_id,
          );
          return;
        }

        setState({
          status: "selecting",
          workspaces,
        });
      } catch {
        setState({
          status: "error",
          message:
            "We couldn't load your workspaces. Please try again.",
        });
      }
    }, [enterWorkspace]);

  useEffect(() => {
    if (auth.status !== "authenticated") {
      return;
    }

    void Promise.resolve().then(
      loadAccessibleWorkspaces,
    );
  }, [
    auth.status,
    loadAccessibleWorkspaces,
  ]);

  async function handleCreateWorkspace(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (creating) {
      return;
    }

    const token =
      window.localStorage.getItem(
        SESSION_TOKEN_KEY,
      );

    if (!token) {
      setCreationError(
        "Your session is no longer available. Please sign in again.",
      );
      return;
    }

    const form =
      new FormData(event.currentTarget);

    const organizationName = String(
      form.get("organizationName") ?? "",
    ).trim();

    const workspaceName = String(
      form.get("workspaceName") ?? "",
    ).trim();

    setCreating(true);
    setCreationError(null);

    try {
      const workspace =
        await createWorkspace(
          token,
          {
            organizationName,
            workspaceName,
          },
        );

      enterWorkspace(
        workspace.workspace_id,
      );
    } catch {
      setCreationError(
        "We couldn't create your workspace. Please try again.",
      );
    } finally {
      setCreating(false);
    }
  }

  if (state.status === "loading") {
    return (
      <div
        role="status"
        aria-live="polite"
      >
        Loading your workspace…
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <main>
        <div role="alert">
          {state.message}
        </div>

        <button
          type="button"
          onClick={() => {
            setState({
              status: "loading",
            });
            void loadAccessibleWorkspaces();
          }}
        >
          Retry
        </button>
      </main>
    );
  }

  if (state.status === "selecting") {
    return (
      <main>
        <h1>Choose a workspace</h1>

        <p>
          Select the workspace you want to
          continue with.
        </p>

        <div>
          {state.workspaces.map(
            (workspace) => (
              <button
                key={workspace.workspace_id}
                type="button"
                onClick={() =>
                  enterWorkspace(
                    workspace.workspace_id,
                  )
                }
              >
                <strong>
                  {workspace.name}
                </strong>
                <span>
                  {workspace.role}
                </span>
              </button>
            ),
          )}
        </div>
      </main>
    );
  }

  return (
    <main>
      <h1>
        Create your first workspace
      </h1>

      <p>
        Set up a workspace to start
        measuring incremental impact.
      </p>

      <form
        onSubmit={
          handleCreateWorkspace
        }
      >
        <label>
          <span>Organization</span>
          <input
            name="organizationName"
            required
            autoComplete="organization"
            placeholder="Northstar Labs"
          />
        </label>

        <label>
          <span>Workspace name</span>
          <input
            name="workspaceName"
            required
            placeholder="Measurement Team"
          />
        </label>

        {creationError && (
          <div role="alert">
            {creationError}
          </div>
        )}

        <button
          type="submit"
          disabled={creating}
        >
          {creating
            ? "Creating workspace…"
            : "Create workspace"}
        </button>
      </form>
    </main>
  );
}
