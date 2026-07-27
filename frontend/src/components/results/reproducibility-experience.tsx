"use client";

import { useState } from "react";
import { ArrowRightIcon } from "@phosphor-icons/react/ArrowRight";
import { ChartLineUpIcon } from "@phosphor-icons/react/ChartLineUp";
import { CheckCircleIcon } from "@phosphor-icons/react/CheckCircle";
import { FileTextIcon } from "@phosphor-icons/react/FileText";
import { GitBranchIcon } from "@phosphor-icons/react/GitBranch";
import { WarningCircleIcon } from "@phosphor-icons/react/WarningCircle";
import Link from "next/link";

import {
  analysisResultPath,
  analysisRunPath,
} from "@/lib/projects/routes";
import type {
  AnalysisLineageState,
  AnalysisRunLineageResponse,
} from "@/lib/results/lineage-types";

type Snapshot = Record<string, unknown> | null;

type DisplayRow = {
  label: string;
  rawValue?: string;
  value: string;
};

const unavailableMessage =
  "Unavailable for this historical run.";

function humanize(value: string): string {
  const words = value
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .trim();

  if (!words) return "Unknown";

  return `${words.charAt(0).toUpperCase()}${words.slice(1)}`;
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value < 0) {
    return "—";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  const units = [
    "KB",
    "MB",
    "GB",
    "TB",
  ];

  let amount = value / 1024;
  let unitIndex = 0;

  while (
    amount >= 1024
    && unitIndex < units.length - 1
  ) {
    amount /= 1024;
    unitIndex += 1;
  }

  return `${new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits: 1,
    },
  ).format(amount)} ${units[unitIndex]}`;
}

function displayValue(value: unknown): string {
  if (
    value === null
    || value === undefined
  ) {
    return "—";
  }

  if (typeof value === "string") {
    return value.trim() || "—";
  }

  if (typeof value === "number") {
    return new Intl.NumberFormat(
      "en-US",
      {
        maximumFractionDigits: 4,
      },
    ).format(value);
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return "None";
    }

    return value
      .map((item) => displayValue(item))
      .join(", ");
  }

  if (typeof value === "object") {
    return Object.entries(
      value as Record<string, unknown>,
    )
      .slice(0, 4)
      .map(
        ([key, item]) =>
          `${humanize(key)}: ${displayValue(item)}`,
      )
      .join(" · ");
  }

  return String(value);
}

function snapshotRows(
  snapshot: Snapshot,
  preferredKeys: string[],
  limit = 6,
): DisplayRow[] {
  if (snapshot === null) {
    return [];
  }

  const orderedKeys = [
    ...preferredKeys.filter(
      (key) =>
        Object.prototype.hasOwnProperty.call(
          snapshot,
          key,
        ),
    ),
    ...Object.keys(snapshot).filter(
      (key) =>
        !preferredKeys.includes(key),
    ),
  ];

  return orderedKeys
    .slice(0, limit)
    .map((key) => {
      const raw = snapshot[key];

      const shouldHumanize =
        typeof raw === "string"
        && (
          key.endsWith("_type")
          || key.endsWith("_method")
          || key.endsWith("_rule")
        );

      return {
        label: humanize(key),
        rawValue:
          typeof raw === "string"
            ? raw
            : undefined,
        value:
          shouldHumanize
            ? humanize(raw)
            : displayValue(raw),
      };
    });
}

function isLegacy(
  data: AnalysisRunLineageResponse,
): boolean {
  return [
    data.semantic_mapping_snapshot,
    data.analysis_period_snapshot,
    data.analysis_selection_snapshot,
    data.treatment_control_snapshot,
    data.estimand_snapshot,
  ].some(
    (snapshot) => snapshot === null,
  );
}

function shortValue(value: string): string {
  if (value.length <= 22) {
    return value;
  }

  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}

function StateView({
  title,
}: {
  title: string;
}) {
  return (
    <main className="state-shell">
      <section className="state-card">
        <p className="eyebrow">
          Reproducibility
        </p>

        <h1>{title}</h1>
      </section>
    </main>
  );
}

function CopyField({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  const [
    copied,
    setCopied,
  ] = useState(false);

  function copy() {
    void navigator.clipboard?.writeText(
      value,
    );

    setCopied(true);

    window.setTimeout(
      () => {
        setCopied(false);
      },
      1600,
    );
  }

  return (
    <article className="repro-copy-field">
      <div>
        <span>{label}</span>

        <strong title={value}>
          {shortValue(value)}
        </strong>

        {(
          label === "Input fingerprint"
          || label === "Dataset checksum"
        ) && shortValue(value) !== value ? (
          <span className="repro-visually-hidden">
            {value}
          </span>
        ) : null}

      </div>

      <button
        type="button"
        onClick={copy}
        aria-label={`Copy ${label.toLowerCase()}`}
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </article>
  );
}

function DataRows({
  exposeRawValues = false,
  rows,
}: {
  exposeRawValues?: boolean;
  rows: DisplayRow[];
}) {
  return (
    <dl className="repro-data-list">
      {rows.map((row) => (
        <div key={`${row.label}:${row.value}`}>
          <dt>{row.label}</dt>

          <dd title={row.rawValue}>
            {row.value}

            {(
              exposeRawValues
              && row.rawValue
              && row.rawValue !== row.value
            ) ? (
              <span className="repro-visually-hidden">
                {row.rawValue}
              </span>
            ) : null}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function OverviewCard({
  eyebrow,
  exposeRawValues = false,
  footer,
  icon,
  id,
  rows,
  title,
}: {
  eyebrow: string;
  exposeRawValues?: boolean;
  footer?: React.ReactNode;
  icon: React.ReactNode;
  id?: string;
  rows: DisplayRow[];
  title: string;
}) {
  return (
    <article
      className="repro-overview-card"
      id={id}
    >
      <header className="repro-card-header">
        <span
          className="repro-card-icon"
          aria-hidden="true"
        >
          {icon}
        </span>

        <div>
          <p>{eyebrow}</p>
          <h2>{title}</h2>
        </div>
      </header>

      <DataRows
        exposeRawValues={exposeRawValues}
        rows={rows}
      />

      {footer ? (
        <footer className="repro-card-footer">
          {footer}
        </footer>
      ) : null}
    </article>
  );
}

function SnapshotCard({
  eyebrow,
  exposeRawValues = false,
  icon,
  id,
  preferredKeys,
  snapshot,
  title,
}: {
  eyebrow: string;
  exposeRawValues?: boolean;
  icon: React.ReactNode;
  id?: string;
  preferredKeys: string[];
  snapshot: Snapshot;
  title: string;
}) {
  const rows = snapshotRows(
    snapshot,
    preferredKeys,
  );

  return (
    <article
      className="repro-overview-card"
      id={id}
    >
      <header className="repro-card-header">
        <span
          className="repro-card-icon"
          aria-hidden="true"
        >
          {icon}
        </span>

        <div>
          <p>{eyebrow}</p>
          <h2>{title}</h2>
        </div>
      </header>

      {snapshot === null ? (
        <div className="repro-unavailable">
          <WarningCircleIcon
            aria-hidden="true"
            size={18}
            weight="fill"
          />

          <p>{unavailableMessage}</p>
        </div>
      ) : (
        <DataRows
          exposeRawValues={exposeRawValues}
          rows={rows}
        />
      )}
    </article>
  );
}

export function ReproducibilityExperience({
  analysisRunId,
  projectId,
  reportsAvailable = false,
  resultAvailable = false,
  state,
  workspaceId,
}: {
  analysisRunId?: string;
  projectId?: string;
  reportsAvailable?: boolean;
  resultAvailable?: boolean;
  state: AnalysisLineageState;
  workspaceId?: string;
}) {
  if (state.kind === "loading") {
    return (
      <StateView title="Loading reproducibility lineage" />
    );
  }

  if (state.kind === "permission") {
    return (
      <StateView title="You don’t have access to this lineage" />
    );
  }

  if (state.kind === "missing") {
    return (
      <StateView title="Reproducibility lineage was not found" />
    );
  }

  if (state.kind === "error") {
    return (
      <StateView title="Reproducibility details are temporarily unavailable" />
    );
  }

  const data = state.data;
  const legacy = isLegacy(data);

  const libraries = Object.entries(
    data.statistical_library_versions ?? {},
  ).sort(
    ([left], [right]) =>
      left.localeCompare(right),
  );

  const statusHref =
    workspaceId
    && projectId
    && analysisRunId
      ? analysisRunPath(
          workspaceId,
          projectId,
          analysisRunId,
        )
      : null;

  const resultHref =
    workspaceId
    && projectId
    && analysisRunId
      ? analysisResultPath(
          workspaceId,
          projectId,
          analysisRunId,
        )
      : null;

  const reportsHref =
    statusHref
      ? `${statusHref}/reports`
      : null;

  const estimatorRows: DisplayRow[] = [
    {
      label: "Estimator",
      rawValue: data.estimator_type,
      value: humanize(
        data.estimator_type,
      ),
    },
    {
      label: "Estimator version",
      value: data.estimator_version,
    },
    {
      label: "Random seed",
      value: String(data.random_seed),
    },
    ...snapshotRows(
      data.estimator_configuration,
      [
        "formula",
        "model",
        "method",
        "confidence_level",
        "standard_error_type",
      ],
      8,
    ).filter(
      (row) =>
        !row.label.toLowerCase().includes("date")
        && !row.label.toLowerCase().includes("period")
        && ![
          "Estimator",
          "Estimator type",
          "Estimator version",
          "Random seed",
        ].includes(row.label),
    ).slice(0, 3),
  ];

  const datasetRows: DisplayRow[] = [
    {
      label: "Dataset ID",
      value: data.dataset_id,
    },
    {
      label: "Dataset size",
      value: formatBytes(
        data.dataset_byte_size,
      ),
    },
    {
      label: "Semantic mapping ID",
      value: data.semantic_mapping_id,
    },
    {
      label: "Mapping version",
      value: `v${data.semantic_mapping_version}`,
    },
  ];

  const runtimeRows: DisplayRow[] = [
    {
      label: "Application version",
      value: data.application_version,
    },
    {
      label: "Source revision",
      value: data.source_revision,
    },
    {
      label: "Created on",
      value: formatDate(
        data.created_at,
      ),
    },
    {
      label: "Libraries",
      value:
        libraries.length > 0
          ? `${libraries.length} recorded`
          : "None recorded",
    },
  ];

  return (
    <main className="results-shell reproducibility-page">
      <header className="repro-page-header">
        <div>
          <p className="repro-page-kicker">
            Read-only execution receipt
          </p>

          <h1>
            Reproducibility and lineage
          </h1>

          <p>
            Everything needed to understand,
            audit, and reproduce this analysis
            from its persisted inputs.
          </p>
        </div>

        {statusHref ? (
          <nav
            className="repro-page-actions"
            aria-label="Analysis run navigation"
          >
            <Link
              href={statusHref}
              className="repro-action"
            >
              View Analysis Status
            </Link>

            {resultAvailable
              && resultHref ? (
                <Link
                  href={resultHref}
                  className="repro-action"
                >
                  View Results
                </Link>
              ) : null}

            {reportsAvailable
              && reportsHref ? (
                <Link
                  href={reportsHref}
                  className="repro-action repro-action-primary"
                >
                  View Reports
                  <ArrowRightIcon
                    aria-hidden="true"
                    size={16}
                    weight="bold"
                  />
                </Link>
              ) : null}
          </nav>
        ) : null}
      </header>

      <section
        className={`repro-status-card ${
          legacy
            ? "is-legacy"
            : "is-verified"
        }`}
        aria-labelledby="repro-status-title"
      >
        <div className="repro-status-main">
          <span
            className="repro-status-icon"
            aria-hidden="true"
          >
            {legacy ? (
              <WarningCircleIcon
                size={28}
                weight="fill"
              />
            ) : (
              <CheckCircleIcon
                size={28}
                weight="fill"
              />
            )}
          </span>

          <div>
            <p>
              Reproducibility status
            </p>

            <div className="repro-status-title-row">
              <h2 id="repro-status-title">
                {legacy
                  ? "Legacy run"
                  : "Verified"}
              </h2>

              <span>
                {legacy
                  ? "Partial lineage"
                  : "All lineage captured"}
              </span>
            </div>

            <small>
              {legacy
                ? "Some lineage fields are unavailable for this historical run."
                : "The persisted configuration and execution lineage are available below."}
            </small>
          </div>
        </div>

        <dl className="repro-status-metadata">
          <div>
            <dt>Analysis ID</dt>
            <dd>{data.analysis_run_id}</dd>
          </div>

          <div>
            <dt>Created on</dt>
            <dd>
              {formatDate(
                data.created_at,
              )}
            </dd>
          </div>

          <div>
            <dt>Receipt type</dt>
            <dd>
              Read-only
            </dd>
          </div>
        </dl>
      </section>

      <nav
        className="repro-tabs"
        aria-label="Reproducibility sections"
      >
        <a href="#overview">
          Overview
        </a>

        <a href="#configuration">
          Configuration snapshots
        </a>

        <a href="#environment">
          Environment
        </a>

        <a href="#lineage">
          Lineage
        </a>
      </nav>

      <section
        className="repro-section"
        id="overview"
        aria-labelledby="execution-identity-title"
      >
        <div className="repro-section-heading">
          <div>
            <p>Immutable identifiers</p>
            <h2 id="execution-identity-title">
              Execution identity
            </h2>
          </div>

          <span>
            Complete values are copied,
            even when visually shortened.
          </span>
        </div>

        <div className="repro-copy-grid">
          <CopyField
            label="Analysis run ID"
            value={data.analysis_run_id}
          />

          <CopyField
            label="Input fingerprint"
            value={
              data.input_fingerprint_sha256
            }
          />

          <CopyField
            label="Dataset checksum"
            value={
              data.dataset_checksum_sha256
            }
          />

          <CopyField
            label="Source revision"
            value={data.source_revision}
          />
        </div>
      </section>

      <section
        className="repro-card-grid"
        aria-label="Reproducibility overview"
      >
        <OverviewCard
          eyebrow="Dataset"
          icon={
            <FileTextIcon
              size={20}
              weight="bold"
            />
          }
          rows={datasetRows}
          title="Dataset lineage"
        />

        <OverviewCard
          eyebrow="Analysis method"
          exposeRawValues
          icon={
            <ChartLineUpIcon
              size={20}
              weight="bold"
            />
          }
          rows={estimatorRows}
          title="Analysis specification"
        />

        <SnapshotCard
          eyebrow="Timeline"
          icon={
            <CheckCircleIcon
              size={20}
              weight="bold"
            />
          }
          preferredKeys={[
            "analysis_start_date",
            "intervention_date",
            "analysis_end_date",
            "pre_period_start",
            "pre_period_end",
            "post_period_start",
            "post_period_end",
          ]}
          snapshot={
            data.analysis_period_snapshot
          }
          title="Analysis period snapshot"
        />

        <OverviewCard
          eyebrow="Runtime"
          icon={
            <GitBranchIcon
              size={20}
              weight="bold"
            />
          }
          id="environment"
          rows={runtimeRows}
          title="Runtime environment"
          footer={
            libraries.length > 0 ? (
              <ul className="repro-library-list">
                {libraries.map(
                  ([name, version]) => (
                    <li key={name}>
                      {name} {version}
                    </li>
                  ),
                )}
              </ul>
            ) : (
              <p className="repro-card-empty">
                No persisted statistical library versions are available.
              </p>
            )
          }
        />
      </section>

      <section
        className="repro-section"
        id="configuration"
        aria-labelledby="configuration-title"
      >
        <div className="repro-section-heading">
          <div>
            <p>Saved analysis inputs</p>
            <h2 id="configuration-title">
              Configuration snapshots
            </h2>
          </div>

          <span>
            These values come from the
            persisted analysis run.
          </span>
        </div>

        <div className="repro-card-grid">
          <SnapshotCard
            eyebrow="Columns and roles"
            icon={
              <FileTextIcon
                size={20}
                weight="bold"
              />
            }
            preferredKeys={[
              "time_column",
              "unit_column",
              "treatment_column",
              "outcome_column",
              "covariates",
            ]}
            snapshot={
              data.semantic_mapping_snapshot
            }
            title="Semantic mapping snapshot"
          />

          <SnapshotCard
            eyebrow="Population and filters"
            icon={
              <ChartLineUpIcon
                size={20}
                weight="bold"
              />
            }
            preferredKeys={[
              "included_markets",
              "included_units",
              "treated_markets",
              "treated_units",
              "control_markets",
              "control_units",
              "row_filters",
              "segment_filters",
            ]}
            snapshot={
              data.analysis_selection_snapshot
            }
            title="Analysis selection snapshot"
          />

          <SnapshotCard
            eyebrow="Assignment"
            icon={
              <CheckCircleIcon
                size={20}
                weight="bold"
              />
            }
            preferredKeys={[
              "assignment_rule",
              "treatment_value",
              "control_value",
              "assignment_date",
              "intervention_date",
            ]}
            snapshot={
              data.treatment_control_snapshot
            }
            title="Treatment and control snapshot"
          />

          <SnapshotCard
            eyebrow="Target effect"
            exposeRawValues
            icon={
              <GitBranchIcon
                size={20}
                weight="bold"
              />
            }
            preferredKeys={[
              "estimand_type",
              "target_outcome",
              "target_population",
              "effect_scale",
            ]}
            snapshot={
              data.estimand_snapshot
            }
            title="Estimand"
          />
        </div>
      </section>

      <section className="repro-boundary">
        <span aria-hidden="true">
          <CheckCircleIcon
            size={23}
            weight="fill"
          />
        </span>

        <div>
          <p>
            Reproducibility boundary
          </p>

          <h2>
            Complete persisted lineage,
            with a clear numerical boundary.
          </h2>

          <span>
            Matching lineage captures the immutable inputs,
            random seed, application version, source revision,
            and statistical library versions used for this analysis.
            It does not guarantee bit-for-bit identical results across
            different hardware, operating systems or numerical backends.
          </span>
        </div>
      </section>

      <details
        className="repro-lineage-details"
        id="lineage"
      >
        <summary>
          <span>
            <GitBranchIcon
              aria-hidden="true"
              size={21}
              weight="bold"
            />

            <span>
              <strong>
                Full persisted lineage
              </strong>

              <small>
                Complete technical record of
                configuration and execution
              </small>
            </span>
          </span>

          <span>
            Expand lineage
          </span>
        </summary>

        <pre>
          {JSON.stringify(
            data,
            null,
            2,
          )}
        </pre>
      </details>
    </main>
  );
}
