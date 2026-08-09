"use client";

import {
  DownloadSimpleIcon,
  FunnelSimpleIcon,
  MagnifyingGlassIcon,
} from "@phosphor-icons/react";
import { useAnalysisResult } from "@/lib/results/use-analysis-result";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { type ExplorerOptions, queueReport } from "@/lib/data-products/api";
import {
  useDatasetExplorer,
  useReports,
} from "@/lib/data-products/use-data-products";
import {
  datasetEstimatorPreferenceKey,
  datasetMappingPath,
  datasetQualityPath,
} from "../../lib/datasets/routes";
import { DataExplorer } from "./data-explorer";
import { ReportHistory } from "./report-history";

type FilterOperator = NonNullable<ExplorerOptions["filterOperator"]>;

type SavedExplorerView = {
  name: string;
  search: string;
  sortColumn: string;
  descending: boolean;
  filterColumn: string;
  filterOperator: FilterOperator;
  filterValue: string;
  outcomeColumn: string;
};

function explorerParameter(name: string): string {
  if (typeof window === "undefined") {
    return "";
  }
  return new URLSearchParams(window.location.search).get(name) ?? "";
}

function savedExplorerViews(datasetId: string): SavedExplorerView[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const stored = JSON.parse(
      localStorage.getItem(`incrementality_explorer_views_${datasetId}`) ??
        "[]",
    );
    return Array.isArray(stored) ? (stored as SavedExplorerView[]) : [];
  } catch {
    return [];
  }
}

export function ExplorerClient({
  workspaceId,
  projectId,
  datasetId,
}: {
  workspaceId: string;
  projectId: string;
  datasetId: string;
}) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState(() => explorerParameter("columns"));
  const [sortColumn, setSortColumn] = useState(() => explorerParameter("sort"));
  const [descending, setDescending] = useState(
    () => explorerParameter("direction") === "desc",
  );
  const [filterColumn, setFilterColumn] = useState(() =>
    explorerParameter("filter"),
  );
  const [filterOperator, setFilterOperator] = useState<FilterOperator>(() =>
    explorerParameter("operator") === "is_missing" ? "is_missing" : "contains",
  );
  const [filterValue, setFilterValue] = useState(() =>
    explorerParameter("value"),
  );
  const [outcomeColumn, setOutcomeColumn] = useState(() =>
    explorerParameter("outcome"),
  );
  const [interventionDate, setInterventionDate] = useState(() =>
    explorerParameter("intervention"),
  );
  const [estimator, setEstimator] = useState(() =>
    explorerParameter("estimator") === "marketing_mix_model"
      ? "marketing_mix_model"
      : typeof window !== "undefined" &&
          window.localStorage.getItem(
            datasetEstimatorPreferenceKey(datasetId),
          ) === "marketing_mix_model"
        ? "marketing_mix_model"
        : "difference_in_differences",
  );
  const [viewName, setViewName] = useState("");
  const [selectedView, setSelectedView] = useState("");
  const [savedViews, setSavedViews] = useState<SavedExplorerView[]>(() =>
    savedExplorerViews(datasetId),
  );
  const usesInterventionDate = estimator !== "marketing_mix_model";
  const effectiveInterventionDate = usesInterventionDate
    ? interventionDate
    : "";

  const options = useMemo<ExplorerOptions>(
    () => ({
      page,
      search,
      sortColumn,
      descending,
      filterColumn,
      filterOperator,
      filterValue,
      outcomeColumn,
      interventionDate: effectiveInterventionDate,
      estimator,
    }),
    [
      page,
      search,
      sortColumn,
      descending,
      filterColumn,
      filterOperator,
      filterValue,
      outcomeColumn,
      effectiveInterventionDate,
      estimator,
    ],
  );

  const clearInvalidInterventionDate = useCallback((rejectedValue: string) => {
    setInterventionDate((currentValue) =>
      currentValue === rejectedValue ? "" : currentValue,
    );
  }, []);

  const { state, quality, versions, dataset } = useDatasetExplorer(
    workspaceId,
    projectId,
    datasetId,
    options,
    estimator,
    clearInvalidInterventionDate,
  );
  const base =
    `/api/v1/workspaces/${workspaceId}/projects/${projectId}` +
    `/datasets/${datasetId}`;
  const currentPage = state.kind === "ready" ? state.data.page : page;
  const totalPages = state.kind === "ready" ? state.data.total_pages : 1;
  const columns = state.kind === "ready" ? state.data.columns : [];

  useEffect(() => {
    window.localStorage.setItem(
      datasetEstimatorPreferenceKey(datasetId),
      estimator,
    );
    const params = new URLSearchParams();
    if (search) params.set("columns", search);
    if (sortColumn) params.set("sort", sortColumn);
    if (descending) params.set("direction", "desc");
    if (filterColumn) params.set("filter", filterColumn);
    if (filterOperator !== "contains") {
      params.set("operator", filterOperator);
    }
    if (filterValue && filterOperator === "contains") {
      params.set("value", filterValue);
    }
    if (outcomeColumn) params.set("outcome", outcomeColumn);
    if (estimator === "marketing_mix_model") {
      params.set("estimator", estimator);
    }

    if (effectiveInterventionDate) {
      params.set("intervention", effectiveInterventionDate);
    }
    const query = params.toString();
    window.history.replaceState(
      null,
      "",
      query ? `${window.location.pathname}?${query}` : window.location.pathname,
    );
  }, [
    search,
    sortColumn,
    descending,
    filterColumn,
    filterOperator,
    filterValue,
    outcomeColumn,
    effectiveInterventionDate,
    estimator,
    datasetId,
  ]);

  const changeVersion = (id: string) => {
    if (id !== datasetId) {
      window.location.assign(
        `/workspaces/${workspaceId}/projects/${projectId}` +
          `/datasets/${id}/explore`,
      );
    }
  };

  const filterMissing = (column: string) => {
    setFilterColumn(column);
    setFilterOperator("is_missing");
    setFilterValue("");
    setPage(1);
  };

  const clearFilter = () => {
    setFilterColumn("");
    setFilterOperator("contains");
    setFilterValue("");
    setPage(1);
  };

  const saveView = () => {
    const name = viewName.trim();
    if (!name) {
      return;
    }
    const nextView: SavedExplorerView = {
      name,
      search,
      sortColumn,
      descending,
      filterColumn,
      filterOperator,
      filterValue,
      outcomeColumn,
    };
    const nextViews = [
      ...savedViews.filter((view) => view.name !== name),
      nextView,
    ];
    setSavedViews(nextViews);
    setSelectedView(name);
    setViewName("");
    localStorage.setItem(
      `incrementality_explorer_views_${datasetId}`,
      JSON.stringify(nextViews),
    );
  };

  const openSavedView = (name: string) => {
    setSelectedView(name);
    const view = savedViews.find((item) => item.name === name);
    if (!view) {
      return;
    }
    setSearch(view.search);
    setSortColumn(view.sortColumn);
    setDescending(view.descending);
    setFilterColumn(view.filterColumn);
    setFilterOperator(view.filterOperator);
    setFilterValue(view.filterValue);
    setOutcomeColumn(view.outcomeColumn);
    setPage(1);
  };

  const exportQuery = new URLSearchParams({
    descending: String(descending),
    column_search: search,
  });
  if (sortColumn) exportQuery.set("sort_column", sortColumn);
  if (filterColumn) {
    exportQuery.set("filter_column", filterColumn);
    exportQuery.set("filter_operator", filterOperator);
    if (filterOperator === "contains") {
      exportQuery.set("filter_value", filterValue);
    }
  }

  return (
    <main className="results-shell data-explorer-shell">
      <div className="data-explorer-hero">
        <div className="data-explorer-title-block">
          <Header
            title="Data Explorer"
            subtitle="Understand your evidence before you estimate lift. Inspect trends, distributions, missingness, and design readiness in one place."
          />
        </div>

        <nav className="data-explorer-links" aria-label="Dataset navigation">
          <a href={datasetQualityPath(workspaceId, projectId, datasetId)}>
            View Data Quality
          </a>
          <a
            href={datasetMappingPath(
              workspaceId,
              projectId,
              datasetId,
              estimator,
            )}
          >
            Semantic Mapping
          </a>

          <a
            className="explorer-export-primary"
            href={`${base}/preview.csv?${exportQuery}`}
          >
            <DownloadSimpleIcon size={17} aria-hidden="true" />
            Export view
          </a>
        </nav>
      </div>

      <DataExplorer
        state={state}
        quality={quality}
        dataset={dataset}
        versionControl={
          <select
            aria-label="Dataset version"
            value={datasetId}
            onChange={(event) => changeVersion(event.target.value)}
          >
            {versions.length === 0 ? (
              <option value={datasetId}>Current version</option>
            ) : null}

            {versions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.source_filename} ·{" "}
                {new Date(version.created_at).toLocaleDateString()}
              </option>
            ))}
          </select>
        }
        toolbar={
          <section
            className="explorer-controls"
            role="region"
            aria-label="Explore dataset controls"
          >
            <div className="explorer-toolbar-main">
              <label className="explorer-search-field">
                <span className="sr-only">Search columns</span>

                <MagnifyingGlassIcon size={18} aria-hidden="true" />

                <input
                  aria-label="Search columns"
                  placeholder="Search columns..."
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(1);
                  }}
                />
              </label>

              <div className="explorer-filter-group">
                <FunnelSimpleIcon size={17} aria-hidden="true" />

                <label className="explorer-field">
                  <span className="sr-only">Filter column</span>

                  <select
                    aria-label="Filter column"
                    value={filterColumn}
                    onChange={(event) => {
                      setFilterColumn(event.target.value);
                      setFilterOperator("contains");
                      setPage(1);
                    }}
                  >
                    <option value="">Filter rows</option>

                    {columns.map((column) => (
                      <option key={column.name} value={column.name}>
                        {column.name}
                      </option>
                    ))}
                  </select>
                </label>

                {filterOperator === "contains" ? (
                  <input
                    aria-label="Filter value"
                    placeholder="Contains value"
                    value={filterValue}
                    disabled={!filterColumn}
                    onChange={(event) => {
                      setFilterValue(event.target.value);
                      setPage(1);
                    }}
                  />
                ) : (
                  <span className="explorer-active-filter">
                    {filterColumn} is missing
                    <button type="button" onClick={clearFilter}>
                      Clear
                    </button>
                  </span>
                )}
              </div>

              <label className="explorer-field explorer-sort-field">
                <span className="sr-only">Sort column</span>

                <select
                  aria-label="Sort column"
                  value={sortColumn}
                  onChange={(event) => {
                    setSortColumn(event.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">No sorting</option>

                  {columns.map((column) => (
                    <option key={column.name} value={column.name}>
                      Sort by {column.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="explorer-checkbox">
                <input
                  type="checkbox"
                  checked={descending}
                  onChange={(event) => setDescending(event.target.checked)}
                />
                Descending
              </label>

              <div className="explorer-saved-cluster">
                <select
                  aria-label="Saved views"
                  value={selectedView}
                  onChange={(event) => openSavedView(event.target.value)}
                >
                  <option value="">Saved views</option>

                  {savedViews.map((view) => (
                    <option key={view.name} value={view.name}>
                      {view.name}
                    </option>
                  ))}
                </select>

                <input
                  aria-label="Saved view name"
                  placeholder="Name this view"
                  value={viewName}
                  onChange={(event) => setViewName(event.target.value)}
                />

                <button
                  className="explorer-save-view"
                  type="button"
                  disabled={!viewName.trim()}
                  onClick={saveView}
                  aria-label="Save current view"
                >
                  Save
                </button>
              </div>
            </div>
          </section>
        }
        selectedOutcome={outcomeColumn}
        estimator={estimator}
        onEstimatorChange={setEstimator}
        selectedInterventionDate={effectiveInterventionDate}
        onInterventionDateChange={(value) => {
          setInterventionDate(value);

          setPage(1);
        }}
        onOutcomeChange={(column) => {
          setOutcomeColumn(column);
          setPage(1);
        }}
        onFilterMissing={filterMissing}
        exportHref={`${base}/preview.csv?${exportQuery}`}
        onPreviousPage={() => setPage(Math.max(1, currentPage - 1))}
        onNextPage={() => setPage(Math.min(totalPages, currentPage + 1))}
      />
    </main>
  );
}
export function ReportsClient({
  workspaceId,
  projectId,
  runId,
}: {
  workspaceId: string;
  projectId: string;
  runId: string;
}) {
  const [refreshGeneration, setRefreshGeneration] = useState(0);

  const reports = useReports(workspaceId, projectId, runId, refreshGeneration);

  const analysis = useAnalysisResult(workspaceId, projectId, runId);

  const canGenerate =
    analysis.kind === "ready" && analysis.data.lifecycle_status === "succeeded";

  const analysisIsActive =
    analysis.kind === "ready" &&
    (analysis.data.lifecycle_status === "queued" ||
      analysis.data.lifecycle_status === "running" ||
      analysis.data.lifecycle_status === "retrying");

  const generationInFlight = useRef(false);

  const [generatingFormat, setGeneratingFormat] = useState<string | null>(null);

  const generate = async (format: string): Promise<void> => {
    if (!canGenerate || generationInFlight.current) {
      return;
    }

    const token = localStorage.getItem("incrementality_session_token");

    if (!token) {
      return;
    }

    generationInFlight.current = true;
    setGeneratingFormat(format);

    try {
      await queueReport(workspaceId, projectId, runId, format, token);

      setRefreshGeneration((current) => current + 1);
    } finally {
      generationInFlight.current = false;
      setGeneratingFormat(null);
    }
  };

  const isGenerating = generatingFormat !== null;

  return (
    <main className="results-shell">
      <Header
        title="Reports"
        subtitle="Versioned analysis records with diagnostics, quality, limitations, and business impact."
      />

      <nav className="state-actions" aria-label="Analysis report navigation">
        <a
          className="button secondary"
          href={
            `/workspaces/${workspaceId}` +
            `/projects/${projectId}` +
            `/analysis-runs/${runId}` +
            "/result"
          }
        >
          View Results
        </a>

        <a
          className="button secondary"
          href={
            `/workspaces/${workspaceId}` +
            `/projects/${projectId}` +
            `/analysis-runs/${runId}` +
            "/lineage"
          }
        >
          View Reproducibility
        </a>
      </nav>

      {canGenerate ? (
        <div className="filters" aria-busy={isGenerating}>
          <button
            className="button secondary"
            disabled={isGenerating}
            onClick={() => void generate("pdf")}
          >
            {generatingFormat === "pdf" ? "Generating PDF…" : "Generate PDF"}
          </button>

          <button
            className="button secondary"
            disabled={isGenerating}
            onClick={() => void generate("csv")}
          >
            {generatingFormat === "csv" ? "Generating CSV…" : "Generate CSV"}
          </button>
        </div>
      ) : analysisIsActive ? (
        <section className="state-card measurement-state" aria-live="polite">
          <p>Reports will be available after this analysis completes.</p>
        </section>
      ) : null}

      {reports.kind === "loading" ? (
        <section className="state-card measurement-state" aria-live="polite">
          <h1>Loading reports…</h1>
        </section>
      ) : reports.kind === "permission" ? (
        <section className="state-card measurement-state" role="alert">
          <h1>You don’t have access to these reports</h1>
        </section>
      ) : reports.kind === "error" ? (
        <section className="state-card measurement-state" role="alert">
          <h1>Reports are temporarily unavailable</h1>
        </section>
      ) : (
        <ReportHistory
          reports={reports.data}
          workspaceId={workspaceId}
          projectId={projectId}
          runId={runId}
          onRegenerate={canGenerate ? generate : undefined}
          regenerateDisabled={isGenerating}
        />
      )}
    </main>
  );
}

function Header({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="measurement-hero">
      <p className="eyebrow">Measurement evidence</p>
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </header>
  );
}
