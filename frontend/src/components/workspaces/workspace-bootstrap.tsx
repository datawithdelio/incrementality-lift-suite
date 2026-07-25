"use client";

import { ArrowRightIcon } from "@phosphor-icons/react/ArrowRight";
import { BuildingsIcon } from "@phosphor-icons/react/Buildings";
import { WarningCircleIcon } from "@phosphor-icons/react/WarningCircle";
import { useRouter } from "next/navigation";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";
import { toast } from "sonner";

import { useAuth } from "../auth/auth-provider";
import {
  SESSION_TOKEN_KEY,
  WORKSPACE_ID_KEY,
} from "../../lib/auth/api";
import {
  type AccessibleWorkspace,
  createWorkspace,
  listWorkspaces,
  WorkspaceApiError,
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
    useState<{
      title: string;
      message: string;
    } | null>(null);

  const enterWorkspace = useCallback(
    (workspaceId: string) => {
      window.localStorage.setItem(
        WORKSPACE_ID_KEY,
        workspaceId,
      );

      router.push(
        `/workspaces/${workspaceId}`,
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
        {
          title: "Session expired",
          message:
            "Your session is no longer available. Please sign in again.",
        },
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

      toast.success("Workspace created", {
        description: `${workspaceName} is ready for your first project.`,
      });
      enterWorkspace(
        workspace.workspace_id,
      );
    } catch (error) {
      const isConflict =
        error instanceof WorkspaceApiError &&
        error.status === 409;
      const title = isConflict
        ? "Organization URL unavailable"
        : "Workspace not created";
      const message =
        error instanceof WorkspaceApiError
          ? error.message
          : "We couldn't create your workspace. Please try again.";

      setCreationError({ title, message });
      toast.error(title, { description: message });
    } finally {
      setCreating(false);
    }
  }

  if (state.status === "loading") {
    return (
      <div
        className="bootstrap-loading"
        role="status"
        aria-live="polite"
      >
        <span /><span /><span />
        <p>Loading your workspace…</p>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <main className="bootstrap-shell">
        <section className="bootstrap-state">
        <WarningCircleIcon size={26} weight="duotone" aria-hidden="true" />
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
        </section>
      </main>
    );
  }

  if (state.status === "selecting") {
    return (
      <main className="bootstrap-shell">
        <section className="bootstrap-card bootstrap-selector">
        <BuildingsIcon size={28} weight="duotone" aria-hidden="true" />
        <h1>Choose a workspace</h1>

        <p>
          Select the workspace you want to
          continue with.
        </p>

        <div className="bootstrap-workspaces">
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
                <ArrowRightIcon size={17} aria-hidden="true" />
              </button>
            ),
          )}
        </div>
        </section>
      </main>
    );
  }

  return (
    <main className="bootstrap-shell">
      <section className="bootstrap-card">
      <BuildingsIcon size={28} weight="duotone" aria-hidden="true" />
      <h1>
        Create your first workspace
      </h1>

      <p>
        Set up a workspace to start
        measuring incremental impact.
      </p>

      <form className="bootstrap-form"
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
          <div className="bootstrap-error" role="alert">
            <WarningCircleIcon
              size={20}
              weight="fill"
              aria-hidden="true"
            />
            <div>
              <strong>{creationError.title}</strong>
              <span>{creationError.message}</span>
            </div>
          </div>
        )}

        <button className="project-button project-button-primary"
          type="submit"
          disabled={creating}
        >
          {creating
            ? "Creating workspace…"
            : "Create workspace"}
        </button>
      </form>
      </section>
    </main>
  );
}
