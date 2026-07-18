"use client";

import { CaretDownIcon } from "@phosphor-icons/react/CaretDown";
import { CaretUpIcon } from "@phosphor-icons/react/CaretUp";
import { CheckIcon } from "@phosphor-icons/react/Check";
import {
  usePathname,
  useRouter,
} from "next/navigation";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  SESSION_TOKEN_KEY,
  WORKSPACE_ID_KEY,
} from "../../lib/auth/api";
import {
  type AccessibleWorkspace,
  listWorkspaces,
} from "../../lib/workspaces/api";

function workspaceInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "WS";
}

function destinationForWorkspace(
  pathname: string,
  currentWorkspaceId: string,
  nextWorkspaceId: string,
): string {
  const currentPrefix =
    `/workspaces/${currentWorkspaceId}`;

  if (pathname.startsWith(`${currentPrefix}/projects/`)) {
    return `/workspaces/${nextWorkspaceId}`;
  }

  if (pathname.startsWith(currentPrefix)) {
    return pathname.replace(
      currentPrefix,
      `/workspaces/${nextWorkspaceId}`,
    );
  }

  return `/workspaces/${nextWorkspaceId}`;
}

export function WorkspaceSwitcher({
  workspaceId,
}: {
  workspaceId: string;
}) {
  const pathname = usePathname();
  const router = useRouter();

  const [workspaces, setWorkspaces] =
    useState<AccessibleWorkspace[]>([]);

  const [open, setOpen] =
    useState(false);

  const [loadFailed, setLoadFailed] =
    useState(false);

  useEffect(() => {
    let active = true;

    const token =
      window.localStorage.getItem(
        SESSION_TOKEN_KEY,
      );

    if (!token) {
      void Promise.resolve().then(() => {
        if (!active) {
          return;
        }

        setLoadFailed(true);
      });

      return () => {
        active = false;
      };
    }

    void listWorkspaces(token)
      .then((accessibleWorkspaces) => {
        if (!active) {
          return;
        }

        setWorkspaces(
          accessibleWorkspaces,
        );
        setLoadFailed(false);
      })
      .catch(() => {
        if (!active) {
          return;
        }

        setWorkspaces([]);
        setLoadFailed(true);
      });

    return () => {
      active = false;
    };
  }, []);

  const activeWorkspace = useMemo(
    () =>
      workspaces.find(
        (workspace) =>
          workspace.workspace_id ===
          workspaceId,
      ) ?? null,
    [
      workspaces,
      workspaceId,
    ],
  );

  const activeName =
    activeWorkspace?.name ??
    "Current workspace";

  const activeRole =
    activeWorkspace?.role ??
    (loadFailed
      ? "Workspace member"
      : "Loading workspace");

  function switchWorkspace(
    nextWorkspaceId: string,
  ) {
    setOpen(false);

    if (
      nextWorkspaceId === workspaceId
    ) {
      return;
    }

    window.localStorage.setItem(
      WORKSPACE_ID_KEY,
      nextWorkspaceId,
    );

    router.push(
      destinationForWorkspace(
        pathname,
        workspaceId,
        nextWorkspaceId,
      ),
    );
  }

  return (
    <div className="workspace-switcher">
      <span>Workspace</span>

      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() =>
          setOpen((current) => !current)
        }
      >
        <i aria-hidden="true">
          {workspaceInitials(
            activeName,
          )}
        </i>

        <span>
          <strong>
            {activeName}
          </strong>
          <small>
            {activeRole}
          </small>
        </span>

        <b aria-hidden="true">
          {open ? <CaretUpIcon size={14} /> : <CaretDownIcon size={14} />}
        </b>
      </button>

      {open &&
        workspaces.length > 1 && (
          <div
            role="menu"
            aria-label="Switch workspace"
          >
            {workspaces.map(
              (workspace) => (
                <button
                  key={
                    workspace.workspace_id
                  }
                  type="button"
                  role="menuitem"
                  onClick={() =>
                    switchWorkspace(
                      workspace.workspace_id,
                    )
                  }
                >
                  <i aria-hidden="true">
                    {workspaceInitials(
                      workspace.name,
                    )}
                  </i>

                  <span>
                    <strong>
                      {workspace.name}
                    </strong>
                    <small>
                      {workspace.role}
                    </small>
                  </span>

                  {workspace.workspace_id ===
                    workspaceId && (
                    <b aria-hidden="true">
                      <CheckIcon size={14} weight="bold" />
                    </b>
                  )}
                </button>
              ),
            )}
          </div>
        )}
    </div>
  );
}
