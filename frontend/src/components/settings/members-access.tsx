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
  canManageMembers,
} from "@/lib/settings/permissions";
import {
  listWorkspaceMembers,
  listWorkspaces,
  type WorkspaceMember,
  WorkspaceApiError,
} from "@/lib/workspaces/api";

type MembersAccessState =
  | {
      status: "loading";
    }
  | {
      status: "ready";
      members: WorkspaceMember[];
      role: string;
    }
  | {
      status: "restricted";
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

function roleLabel(
  role: string,
): string {
  return (
    role.charAt(0).toUpperCase()
    + role.slice(1)
  );
}

function joinedDate(
  value: string,
): string {
  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en-US",
    {
      year: "numeric",
      month: "short",
      day: "numeric",
    },
  ).format(date);
}

function MembersAccessScope({
  workspaceId,
}: {
  workspaceId: string;
}) {
  const [
    state,
    setState,
  ] = useState<MembersAccessState>({
    status: "loading",
  });

  const load = useCallback(
    async () => {
      const token =
        currentToken();

      if (!token) {
        setState({
          status: "error",
          message:
            "Members and access are unavailable because your session has ended.",
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
              "Members and access are unavailable for this workspace.",
          });
          return;
        }

        if (
          !canManageMembers(
            workspace.role,
          )
        ) {
          setState({
            status: "restricted",
            role:
              workspace.role,
          });
          return;
        }

        const members =
          await listWorkspaceMembers(
            token,
            workspaceId,
          );

        setState({
          status: "ready",
          members,
          role:
            workspace.role,
        });
      } catch (error) {
        setState({
          status: "error",
          message:
            error instanceof WorkspaceApiError
              ? error.message
              : "Members and access are unavailable. Please try again.",
        });
      }
    },
    [
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
            Loading members and access…
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
            Members & Access
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

  if (
    state.status
    === "restricted"
  ) {
    return (
      <main className="project-shell">
        <header className="workspace-heading">
          <div>
            <p className="project-eyebrow">
              Workspace access
            </p>

            <h1>
              Members & Access
            </h1>

            <p>
              Review workspace membership and access controls.
            </p>
          </div>
        </header>

        <section className="project-state-card">
          <h2>
            Member access restricted
          </h2>

          <p>
            You do not have permission to view workspace members.
          </p>

          <p>
            Your current role is{" "}
            <strong>
              {roleLabel(
                state.role,
              )}
            </strong>.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="project-shell">
      <header className="workspace-heading">
        <div>
          <p className="project-eyebrow">
            Workspace access
          </p>

          <h1>
            Members & Access
          </h1>

          <p>
            Review the people who currently have access to this workspace.
          </p>
        </div>
      </header>

      <section
        className="project-section"
        aria-labelledby="workspace-members-heading"
      >
        <div className="project-section-heading">
          <div>
            <h2 id="workspace-members-heading">
              Workspace members
            </h2>

            <p>
              Your role:{" "}
              <strong>
                {roleLabel(
                  state.role,
                )}
              </strong>
            </p>
          </div>
        </div>

        {state.members.length
          === 0 ? (
          <div className="project-state-card">
            <p>
              No workspace members were found.
            </p>
          </div>
        ) : (
          <div className="project-details-card">
            <ul
              aria-label="Workspace members"
            >
              {state.members.map(
                (
                  member,
                ) => (
                  <li
                    key={`${member.email}-${member.role}`}
                  >
                    <div>
                      <strong>
                        {member.display_name}
                      </strong>

                      <p>
                        {member.email}
                      </p>
                    </div>

                    <dl>
                      <div>
                        <dt>
                          Role
                        </dt>

                        <dd>
                          {roleLabel(
                            member.role,
                          )}
                        </dd>
                      </div>

                      <div>
                        <dt>
                          Joined
                        </dt>

                        <dd>
                          {joinedDate(
                            member.joined_at,
                          )}
                        </dd>
                      </div>
                    </dl>
                  </li>
                ),
              )}
            </ul>
          </div>
        )}
      </section>

      <section
        className="project-section"
        aria-labelledby="member-management-heading"
      >
        <div className="project-section-heading">
          <div>
            <h2 id="member-management-heading">
              Member management
            </h2>

            <p>
              Member invitations, role changes, and member removal are not available yet.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

export function MembersAccess({
  workspaceId,
}: {
  workspaceId: string;
}) {
  return (
    <MembersAccessScope
      key={workspaceId}
      workspaceId={workspaceId}
    />
  );
}
