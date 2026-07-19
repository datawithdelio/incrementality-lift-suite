"use client";
import { useAnalysisResult } from "@/lib/results/use-analysis-result";

import {
  datasetMappingPath,
  datasetQualityPath,
} from "../../lib/datasets/routes";
import { useMemo, useRef, useState } from "react";
import { ExplorerOptions, queueReport } from "@/lib/data-products/api";
import { useDatasetExplorer, useReports } from "@/lib/data-products/use-data-products";
import { DataExplorer } from "./data-explorer";
import { ReportHistory } from "./report-history";

export function ExplorerClient({ workspaceId, projectId, datasetId }: { workspaceId: string; projectId: string; datasetId: string }) {
  const [page, setPage] = useState(1); const [search, setSearch] = useState(""); const [sortColumn, setSortColumn] = useState(""); const [descending, setDescending] = useState(false); const [filterColumn, setFilterColumn] = useState(""); const [filterValue, setFilterValue] = useState(""); const [estimator, setEstimator] = useState("difference_in_differences");
  const options = useMemo<ExplorerOptions>(() => ({ page, search, sortColumn, descending, filterColumn, filterValue }), [page, search, sortColumn, descending, filterColumn, filterValue]);
  const { state, quality, versions, dataset } = useDatasetExplorer(workspaceId, projectId, datasetId, options, estimator);
  const base = `/api/v1/workspaces/${workspaceId}/projects/${projectId}/datasets/${datasetId}`;
  const currentPage = state.kind === "ready" ? state.data.page : page;
  const totalPages = state.kind === "ready" ? state.data.total_pages : 1;
  const changeVersion = (id: string) => { if (id !== datasetId) window.location.assign(`/workspaces/${workspaceId}/projects/${projectId}/datasets/${id}/explore`); };
  return <main className="results-shell"><Header title="Data Explorer" subtitle="Inspect structure, distributions, and method readiness before analysis."/><nav aria-label="Dataset navigation">
    <a
      href={datasetQualityPath(
        workspaceId,
        projectId,
        datasetId,
      )}
    >
      View Data Quality
    </a>
    <a
      href={datasetMappingPath(
        workspaceId,
        projectId,
        datasetId,
      )}
    >
      Semantic Mapping
    </a>
  </nav><div className="filters"><select aria-label="Dataset version" value={datasetId} onChange={(event) => changeVersion(event.target.value)}>{versions.map((version) => <option key={version.id} value={version.id}>{version.source_filename} · {new Date(version.created_at).toLocaleDateString()}</option>)}</select><input aria-label="Search columns" placeholder="Search columns" value={search} onChange={(event) => setSearch(event.target.value)}/><input aria-label="Filter column" placeholder="Filter column" value={filterColumn} onChange={(event) => setFilterColumn(event.target.value)}/><input aria-label="Filter value" placeholder="Contains value" value={filterValue} onChange={(event) => setFilterValue(event.target.value)}/><input aria-label="Sort column" placeholder="Sort column" value={sortColumn} onChange={(event) => setSortColumn(event.target.value)}/><label><input type="checkbox" checked={descending} onChange={(event) => setDescending(event.target.checked)}/> Descending</label><select aria-label="Causal method" value={estimator} onChange={(event) => setEstimator(event.target.value)}><option value="difference_in_differences">Difference in Differences</option><option value="synthetic_control">Synthetic Control</option><option value="geo_holdout">Geo Holdout</option><option value="marketing_mix_model">Marketing Mix Modeling</option><option value="off_policy_evaluation">Off-Policy Evaluation</option></select><a className="button secondary" href={`${base}/preview.csv?sort_column=${encodeURIComponent(sortColumn)}&descending=${descending}&filter_column=${encodeURIComponent(filterColumn)}&filter_operator=contains&filter_value=${encodeURIComponent(filterValue)}&column_search=${encodeURIComponent(search)}`}>Export filtered view</a></div><DataExplorer state={state} quality={quality} dataset={dataset}/><div className="pager"><button disabled={currentPage <= 1} onClick={() => setPage(Math.max(1, currentPage - 1))}>Previous</button><button disabled={currentPage >= totalPages} onClick={() => setPage(Math.min(totalPages, currentPage + 1))}>Next</button></div></main>;
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
  const [
    refreshGeneration,
    setRefreshGeneration,
  ] = useState(0);

  const reports = useReports(
    workspaceId,
    projectId,
    runId,
    refreshGeneration,
  );

  const analysis = useAnalysisResult(
    workspaceId,
    projectId,
    runId,
  );

  const canGenerate =
    analysis.kind === "ready"
    && analysis.data.lifecycle_status
      === "succeeded";

  const analysisIsActive =
    analysis.kind === "ready"
    && (
      analysis.data.lifecycle_status
        === "queued"
      || analysis.data.lifecycle_status
        === "running"
      || analysis.data.lifecycle_status
        === "retrying"
    );

  const generationInFlight = useRef(false);

  const [
    generatingFormat,
    setGeneratingFormat,
  ] = useState<string | null>(null);

  const generate = async (
    format: string,
  ): Promise<void> => {
    if (
      !canGenerate
      || generationInFlight.current
    ) {
      return;
    }

    const token = localStorage.getItem(
      "incrementality_session_token",
    );

    if (!token) {
      return;
    }

    generationInFlight.current = true;
    setGeneratingFormat(format);

    try {
      await queueReport(
        workspaceId,
        projectId,
        runId,
        format,
        token,
      );

      setRefreshGeneration(
        (current) => current + 1,
      );
    } finally {
      generationInFlight.current = false;
      setGeneratingFormat(null);
    }
  };

  const isGenerating =
    generatingFormat !== null;

  return (
    <main className="results-shell">
      <Header
        title="Reports"
        subtitle="Versioned analysis records with diagnostics, quality, limitations, and business impact."
      />

      <nav
        className="state-actions"
        aria-label="Analysis report navigation"
      >
        <a
          className="button secondary"
          href={
            `/workspaces/${workspaceId}`
            + `/projects/${projectId}`
            + `/analysis-runs/${runId}`
            + "/result"
          }
        >
          View Results
        </a>

        <a
          className="button secondary"
          href={
            `/workspaces/${workspaceId}`
            + `/projects/${projectId}`
            + `/analysis-runs/${runId}`
            + "/lineage"
          }
        >
          View Reproducibility
        </a>
      </nav>

      {canGenerate ? (
        <div
          className="filters"
          aria-busy={isGenerating}
        >
          <button
            className="button secondary"
            disabled={isGenerating}
            onClick={() => void generate("pdf")}
          >
            {generatingFormat === "pdf"
              ? "Generating PDF…"
              : "Generate PDF"}
          </button>

          <button
            className="button secondary"
            disabled={isGenerating}
            onClick={() => void generate("csv")}
          >
            {generatingFormat === "csv"
              ? "Generating CSV…"
              : "Generate CSV"}
          </button>
        </div>
      ) : analysisIsActive ? (
        <section
          className="state-card measurement-state"
          aria-live="polite"
        >
          <p>
            Reports will be available after this analysis completes.
          </p>
        </section>
      ) : null}

      {reports.kind === "loading" ? (
        <section
          className="state-card measurement-state"
          aria-live="polite"
        >
          <h1>Loading reports…</h1>
        </section>
      ) : reports.kind === "permission" ? (
        <section
          className="state-card measurement-state"
          role="alert"
        >
          <h1>You don’t have access to these reports</h1>
        </section>
      ) : reports.kind === "error" ? (
        <section
          className="state-card measurement-state"
          role="alert"
        >
          <h1>Reports are temporarily unavailable</h1>
        </section>
      ) : (
        <ReportHistory
          reports={reports.data}
          workspaceId={workspaceId}
          projectId={projectId}
          runId={runId}
          onRegenerate={
            canGenerate
              ? generate
              : undefined
          }
          regenerateDisabled={
            isGenerating
          }
        />
      )}
    </main>
  );
}

function Header({ title, subtitle }: { title: string; subtitle: string }) { return <header className="measurement-hero"><p className="eyebrow">Measurement evidence</p><h1>{title}</h1><p>{subtitle}</p></header>; }
