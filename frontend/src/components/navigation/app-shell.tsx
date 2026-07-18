"use client";

import { BellIcon } from "@phosphor-icons/react/Bell";
import { ChartBarIcon } from "@phosphor-icons/react/ChartBar";
import { ChartLineUpIcon } from "@phosphor-icons/react/ChartLineUp";
import { CheckCircleIcon } from "@phosphor-icons/react/CheckCircle";
import { CirclesThreePlusIcon } from "@phosphor-icons/react/CirclesThreePlus";
import { FileTextIcon } from "@phosphor-icons/react/FileText";
import { FolderIcon } from "@phosphor-icons/react/Folder";
import { GaugeIcon } from "@phosphor-icons/react/Gauge";
import { GitBranchIcon } from "@phosphor-icons/react/GitBranch";
import { ListIcon } from "@phosphor-icons/react/List";
import { MagnifyingGlassIcon } from "@phosphor-icons/react/MagnifyingGlass";
import { SignOutIcon } from "@phosphor-icons/react/SignOut";
import { TableIcon } from "@phosphor-icons/react/Table";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { KeyboardEvent as ReactKeyboardEvent, ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "../auth/auth-provider";
import { BrandMark } from "../brand/brand-mark";
import { WorkspaceSwitcher } from "../workspaces/workspace-switcher";

type Destination = {
  label: string;
  description: string;
  href: string;
  icon: ReactNode;
  keywords: string;
};

function workspaceDestinations(workspaceId: string, pathname: string): Destination[] {
  const base: Destination[] = [
    {
      label: "Projects",
      description: "Workspace projects and measurement setup",
      href: `/workspaces/${workspaceId}`,
      icon: <FolderIcon size={18} weight="duotone" />,
      keywords: "projects workspace setup",
    },
    {
      label: "Measurement",
      description: "All measurement runs and their reliability",
      href: `/workspaces/${workspaceId}/results-dashboard`,
      icon: <GaugeIcon size={18} weight="duotone" />,
      keywords: "dashboard runs results measurement",
    },
    {
      label: "Channel performance",
      description: "Incremental return and budget guidance",
      href: `/workspaces/${workspaceId}/channel-performance`,
      icon: <ChartLineUpIcon size={18} weight="duotone" />,
      keywords: "channels spend roas budget performance",
    },
  ];

  const project = pathname.match(/\/projects\/([^/]+)/);
  if (project) {
    base.push({
      label: "Project overview",
      description: "Project details and next measurement step",
      href: `/workspaces/${workspaceId}/projects/${project[1]}`,
      icon: <CirclesThreePlusIcon size={18} weight="duotone" />,
      keywords: "project overview details setup",
    });
  }

  const dataset = pathname.match(/\/projects\/([^/]+)\/datasets\/([^/]+)\/explore/);
  if (dataset) {
    base.push({
      label: "Current data explorer",
      description: "Profile, filter, and validate this dataset",
      href: pathname,
      icon: <TableIcon size={18} weight="duotone" />,
      keywords: "dataset columns profile quality explorer",
    });
  }

  const analysis = pathname.match(/\/projects\/([^/]+)\/analysis-runs\/([^/]+)/);
  if (analysis) {
    const resultHref = `/workspaces/${workspaceId}/projects/${analysis[1]}/analysis-runs/${analysis[2]}`;
    base.push(
      {
        label: "Current analysis result",
        description: "Effect, diagnostics, and business impact",
        href: resultHref,
        icon: <ChartBarIcon size={18} weight="duotone" />,
        keywords: "analysis result effect diagnostics",
      },
      {
        label: "Current analysis reproducibility",
        description: "Inspect persisted lineage and execution fingerprints",
        href: `${resultHref}/lineage`,
        icon: <GitBranchIcon size={18} weight="duotone" />,
        keywords: "lineage reproducibility fingerprint seed versions estimand",
      },
      {
        label: "Current analysis reports",
        description: "Generate and download versioned reports",
        href: `${resultHref}/reports`,
        icon: <FileTextIcon size={18} weight="duotone" />,
        keywords: "pdf csv report export download",
      },
    );
  }

  return base;
}

function currentTitle(pathname: string): string {
  if (pathname.includes("channel-performance")) return "Channel performance";
  if (pathname.includes("/datasets/")) return "Data explorer";
  if (pathname.endsWith("/reports")) return "Reports";
  if (pathname.endsWith("/lineage")) return "Reproducibility";
  if (pathname.includes("/analysis-runs/")) return "Analysis result";
  if (pathname.match(/\/projects\/[^/]+$/)) return "Project overview";
  if (pathname.match(/\/workspaces\/[^/]+$/)) return "Projects";
  return "Measurement overview";
}

export function AppShell({ workspaceId, children }: { workspaceId: string; children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const auth = useAuth();
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeResult, setActiveResult] = useState(0);
  const searchRef = useRef<HTMLInputElement>(null);
  const destinations = useMemo(
    () => workspaceDestinations(workspaceId, pathname),
    [workspaceId, pathname],
  );
  const results = destinations.filter((destination) => {
    const needle = query.trim().toLowerCase();
    return !needle || `${destination.label} ${destination.description} ${destination.keywords}`.toLowerCase().includes(needle);
  });

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
      if (event.key === "Escape") {
        setSearchOpen(false);
        setQuery("");
      }
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    if (searchOpen) window.setTimeout(() => searchRef.current?.focus(), 0);
  }, [searchOpen]);

  function navigate(href: string) {
    setSearchOpen(false);
    setQuery("");
    setMobileOpen(false);
    router.push(href);
  }

  function handleSearchKeys(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (results.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveResult((current) => Math.min(current + 1, results.length - 1));
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveResult((current) => Math.max(current - 1, 0));
    }
    if (event.key === "Enter" && results[activeResult]) {
      event.preventDefault();
      navigate(results[activeResult].href);
    }
  }

  async function signOut() {
    await auth.signOut();
    router.push("/login");
  }

  const primary = destinations.slice(0, 3);
  const contextual = destinations.slice(3);

  return (
    <div className="app-frame">
      {mobileOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <aside className={`app-sidebar ${mobileOpen ? "is-open" : ""}`}>
        <div className="sidebar-brand"><BrandMark inverted /></div>

        <WorkspaceSwitcher workspaceId={workspaceId} />

        <nav className="app-navigation" aria-label="Workspace navigation">
          <p>Measure</p>
          {primary.map((destination) => (
            <Link
              key={destination.href}
              href={destination.href}
              aria-current={pathname === destination.href ? "page" : undefined}
              onClick={() => setMobileOpen(false)}
            >
              <span className="nav-symbol" aria-hidden="true">{destination.icon}</span>
              <span>{destination.label}</span>
            </Link>
          ))}
          {contextual.length > 0 && <p>Current work</p>}
          {contextual.map((destination) => (
            <Link
              key={destination.label}
              href={destination.href}
              aria-current={pathname === destination.href ? "page" : undefined}
              onClick={() => setMobileOpen(false)}
            >
              <span className="nav-symbol" aria-hidden="true">{destination.icon}</span>
              <span>{destination.label.replace("Current ", "")}</span>
            </Link>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="sidebar-user"><span>ME</span><div><strong>Your account</strong><small>Workspace member</small></div></div>
          <button type="button" onClick={() => void signOut()}><SignOutIcon size={16} aria-hidden="true" /> Sign out</button>
        </div>
      </aside>

      <div className="app-stage">
        <header className="app-topbar">
          <div className="topbar-context">
            <button className="mobile-nav-toggle" type="button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><ListIcon size={19} aria-hidden="true" /></button>
            <div><span>Incrementality</span><strong>{currentTitle(pathname)}</strong></div>
          </div>
          <button className="workspace-search-trigger" type="button" aria-label="Search workspace" onClick={() => setSearchOpen(true)}>
            <MagnifyingGlassIcon size={17} aria-hidden="true" /><span>Search workspace</span><kbd>⌘ K</kbd>
          </button>
          <div className="topbar-actions"><span className="environment-dot"><CheckCircleIcon size={13} weight="fill" aria-hidden="true" />Connected</span><button type="button" aria-label="Notifications"><BellIcon size={17} aria-hidden="true" /></button><span className="topbar-avatar">ME</span></div>
        </header>
        <div className="app-content">{children}</div>
      </div>

      {searchOpen && (
        <div className="command-backdrop" role="presentation" onMouseDown={() => { setSearchOpen(false); setQuery(""); }}>
          <section className="command-palette" role="dialog" aria-modal="true" aria-label="Search workspace" onMouseDown={(event) => event.stopPropagation()}>
            <div className="command-input"><MagnifyingGlassIcon size={20} aria-hidden="true" /><input ref={searchRef} role="combobox" aria-label="Search workspace" aria-controls="workspace-search-results" aria-activedescendant={results[activeResult] ? `workspace-result-${activeResult}` : undefined} aria-expanded="true" placeholder="Search pages, reports, and datasets…" value={query} onChange={(event) => { setQuery(event.target.value); setActiveResult(0); }} onKeyDown={handleSearchKeys} /><kbd>ESC</kbd></div>
            <div className="command-results" id="workspace-search-results" role="listbox">
              <p>{query ? "Matching destinations" : "Quick navigation"}</p>
              {results.map((destination, index) => (
                <button id={`workspace-result-${index}`} key={`${destination.label}-${destination.href}`} type="button" role="option" aria-selected={index === activeResult} aria-label={`${destination.label}. ${destination.description}`} onMouseMove={() => setActiveResult(index)} onClick={() => navigate(destination.href)}>
                  <span className="command-symbol" aria-hidden="true">{destination.icon}</span>
                  <span><strong>{destination.label}</strong><small>{destination.description}</small></span>
                  <i aria-hidden="true">↵</i>
                </button>
              ))}
              {results.length === 0 && <div className="command-empty"><strong>No destination found</strong><span>Try “overview,” “channel,” “dataset,” or “report.”</span></div>}
            </div>
            <footer><span><kbd>↑</kbd><kbd>↓</kbd> Navigate</span><span><kbd>↵</kbd> Open</span></footer>
          </section>
        </div>
      )}
    </div>
  );
}
