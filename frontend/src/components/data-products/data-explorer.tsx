"use client";

import { useState } from "react";

import type {
  DataQuality,
  DatasetPreview,
  LoadState,
  QualityFinding,
} from "@/lib/data-products/types";
import type { Dataset } from "@/lib/datasets/api";

import {
  ExplorerVisualizations,
  type VisualizationTab,
} from "./explorer-visualizations";

const number = (value: number) =>
  new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
  }).format(value);

function formatPreviewValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return String(value);
}

function formatDatasetStatus(status: string): string {
  return status
    .replaceAll("_", " ")
    .replace(/^./, (character) => character.toUpperCase());
}

function formatByteSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    return `${number(kilobytes)} KB`;
  }
  return `${number(kilobytes / 1024)} MB`;
}

function formatDate(value: string | null): string {
  return value
    ? new Date(value).toLocaleString()
    : "Not uploaded yet";
}

export function DataExplorer({
  state,
  quality,
  dataset,
  selectedOutcome,
  onOutcomeChange,
  onFilterMissing,
}: {
  state: LoadState<DatasetPreview>;
  quality?: DataQuality;
  dataset?: Dataset;
  selectedOutcome?: string;
  onOutcomeChange?: (column: string) => void;
  onFilterMissing?: (column: string) => void;
}) {
  const [activeTab, setActiveTab] =
    useState<VisualizationTab>("trend");

  if (state.kind === "loading") {
    return <State title="Profiling your dataset" />;
  }
  if (state.kind === "permission") {
    return <State title="You don’t have access to this dataset" />;
  }
  if (state.kind === "error") {
    return <State title="This dataset could not be inspected" />;
  }

  const data = state.data;
  if (!data.total_rows) {
    return <State title="This dataset has no rows" />;
  }

  const names = Object.keys(data.rows[0] ?? {});

  return (
    <div className="data-explorer-content">
      <DatasetSummary
        data={data}
        dataset={dataset}
        quality={quality}
      />

      <ColumnProfiles data={data} />

      {data.visualizations ? (
        <ExplorerVisualizations
          visualizations={data.visualizations}
          columns={data.columns}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          selectedOutcome={selectedOutcome}
          onOutcomeChange={onOutcomeChange}
          onFilterMissing={onFilterMissing}
        />
      ) : (
        <DistributionPanels data={data} />
      )}

      {quality ? (
        <QualityPanel
          quality={quality}
          onOpenTab={setActiveTab}
        />
      ) : null}

      <section
        className="panel explorer-table"
        aria-labelledby="explorer-table-heading"
      >
        <div className="explorer-section-heading">
          <div>
            <p className="eyebrow">Row-level evidence</p>
            <h2 id="explorer-table-heading">
              Inspect filtered rows
            </h2>
            <p>
              Verify individual observations behind the profile and
              charts.
            </p>
          </div>
          <span className="explorer-page-status">
            Page {number(data.page)} of {number(data.total_pages)}
          </span>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {names.map((name) => (
                  <th key={name}>{name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, index) => (
                <tr key={index}>
                  {names.map((name) => (
                    <td
                      key={name}
                      data-missing={
                        row[name] === null
                        || row[name] === undefined
                        || row[name] === ""
                      }
                    >
                      {formatPreviewValue(row[name])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function DatasetSummary({
  data,
  dataset,
  quality,
}: {
  data: DatasetPreview;
  dataset?: Dataset;
  quality?: DataQuality;
}) {
  return (
    <section
      className="explorer-summary"
      aria-label="Dataset summary"
    >
      <article className="explorer-summary-primary">
        <span>Dataset</span>
        <strong>
          {dataset?.source_filename ?? "Selected dataset"}
        </strong>
        {dataset ? (
          <small className="explorer-summary-detail">
            <span>{formatByteSize(dataset.byte_size)}</span>
            <span>{formatDatasetStatus(dataset.status)}</span>
          </small>
        ) : (
          <small>Profile ready</small>
        )}
      </article>
      <article>
        <span>Rows</span>
        <strong>
          {dataset
            ? number(dataset.row_count ?? data.total_rows)
            : `${number(data.total_rows)} rows`}
        </strong>
        {dataset ? (
          <small className="explorer-summary-detail">
            <span>
              {number(dataset.column_count ?? data.columns.length)}
            </span>
            <span>columns</span>
          </small>
        ) : (
          <small>{number(data.columns.length)} columns</small>
        )}
      </article>
      <article>
        <span>Date range</span>
        <strong>
          {data.date_range
            ? `${data.date_range.minimum} – ${data.date_range.maximum}`
            : "Not detected"}
        </strong>
        {dataset ? (
          <small className="explorer-summary-detail">
            <span>Uploaded</span>
            <span>{formatDate(dataset.uploaded_at)}</span>
          </small>
        ) : (
          <small>Map a date column to enable trends</small>
        )}
      </article>
      <article data-ready={quality?.ready}>
        <span>Method readiness</span>
        <strong>
          {quality ? `${quality.score}/100` : "Assessing"}
        </strong>
        <small>
          {quality
            ? quality.ready
              ? "Ready for analysis"
              : "Action required"
            : "Running quality checks"}
        </small>
      </article>
    </section>
  );
}

function ColumnProfiles({ data }: { data: DatasetPreview }) {
  return (
    <details className="panel profile-strip">
      <summary>
        <span>
          <strong>Column profiles</strong>
          <small>
            Types, missingness, range, and cardinality
          </small>
        </span>
        <span>{data.columns.length} columns</span>
      </summary>
      <div>
        {data.columns.map((column) => (
          <article key={column.name}>
            <strong>{column.name}</strong>
            <span>{column.inferred_type}</span>
            <small>
              {number(column.missing_percentage)}% missing ·{" "}
              {number(column.unique_count)} unique
            </small>
            <small>
              Min {String(column.minimum ?? "—")} · Max{" "}
              {String(column.maximum ?? "—")}
            </small>
            {column.mean !== null ? (
              <small>
                Mean {number(column.mean)} · Median{" "}
                {number(column.median ?? 0)}
              </small>
            ) : null}
          </article>
        ))}
      </div>
    </details>
  );
}

function DistributionPanels({ data }: { data: DatasetPreview }) {
  const treatment = Object.entries(data.treatment_distribution);
  const maximum = Math.max(
    1,
    ...treatment.map(([, count]) => count),
  );
  return (
    <section className="distribution-grid">
      <article className="panel">
        <p className="eyebrow">Treatment and control</p>
        <h2>Group distribution</h2>
        <div className="distribution-bars">
          {treatment.map(([group, count]) => (
            <div key={group}>
              <span>{group}</span>
              <i>
                <b
                  style={{
                    width: `${(count / maximum) * 100}%`,
                  }}
                />
              </i>
              <strong>{number(count)}</strong>
            </div>
          ))}
        </div>
      </article>
      <article className="panel">
        <p className="eyebrow">Outcome distribution</p>
        <h2>Range and center</h2>
        <div className="technical-grid">
          {Object.entries(data.outcome_distribution).map(
            ([metric, value]) => (
              <div className="metric" key={metric}>
                <span>{metric}</span>
                <strong>{number(value)}</strong>
              </div>
            ),
          )}
        </div>
      </article>
    </section>
  );
}

const FINDING_ACTIONS: Record<
  string,
  { tab: VisualizationTab; label: string }
> = {
  missing_data: {
    tab: "missingness",
    label: "View affected columns",
  },
  outliers: {
    tab: "distribution",
    label: "Inspect distribution",
  },
  date_gaps: {
    tab: "trend",
    label: "View timeline",
  },
  treatment_control_balance: {
    tab: "trend",
    label: "Compare groups",
  },
  pre_post_periods: {
    tab: "trend",
    label: "Open trend chart",
  },
};

function findingEvidence(finding: QualityFinding): string {
  const evidence = finding.evidence;
  const phrases: string[] = [];
  const labels: Record<string, string> = {
    gap_count: "gaps detected",
    missing_count: "affected rows",
    outlier_count: "possible outliers",
    pre_periods: "pre-treatment periods",
    post_periods: "post-treatment periods",
    sample_size: "observations",
  };

  Object.entries(labels).forEach(([key, label]) => {
    const value = evidence[key];
    if (typeof value === "number") {
      phrases.push(`${number(value)} ${label}`);
    }
  });

  if (phrases.length > 0) {
    return phrases.slice(0, 2).join(" · ");
  }
  return finding.passed
    ? "No blocking issue detected."
    : "Review the evidence before running an analysis.";
}

function QualityPanel({
  quality,
  onOpenTab,
}: {
  quality: DataQuality;
  onOpenTab: (tab: VisualizationTab) => void;
}) {
  return (
    <section
      className="panel quality-panel"
      aria-labelledby="quality-heading"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Method readiness</p>
          <h2 id="quality-heading">
            {quality.ready
              ? "Ready to analyze"
              : "Fix blocking issues first"}
          </h2>
          <p>
            Every check stays visible so the score never hides a weak
            design.
          </p>
        </div>
        <strong>{quality.score}/100</strong>
      </div>
      <div className="finding-list">
        {quality.findings.map((item) => {
          const action = FINDING_ACTIONS[item.rule_id];
          return (
            <article
              className={item.severity}
              key={item.rule_id}
            >
              <span>
                {item.passed ? "Passed" : item.severity}
              </span>
              <strong>
                {item.rule_id.replaceAll("_", " ")}
              </strong>
              <p className="finding-evidence">
                {findingEvidence(item)}
              </p>
              <p>{item.recommendation}</p>
              {action ? (
                <button
                  type="button"
                  onClick={() => onOpenTab(action.tab)}
                >
                  {action.label}
                </button>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function State({ title }: { title: string }) {
  return (
    <section className="state-card measurement-state">
      <p className="eyebrow">Data Explorer</p>
      <h1>{title}</h1>
    </section>
  );
}
