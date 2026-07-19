"use client";

import Link from "next/link";

import {
  analysisResultPath,
  analysisRunPath,
} from "@/lib/projects/routes";



import type {
  AnalysisLineageState,
  AnalysisRunLineageResponse,
} from "@/lib/results/lineage-types";

function value(
  source: Record<string, unknown> | null,
  key: string,
): string {
  const item = source?.[key];

  if (
    typeof item === "string" ||
    typeof item === "number"
  ) {
    return String(item);
  }

  return "—";
}

function Snapshot({
  title,
  snapshot,
}: {
  title: string;
  snapshot: Record<string, unknown> | null;
}) {
  return (
    <article className="panel">
      <p className="eyebrow">{title}</p>

      {snapshot === null ? (
        <p>Unavailable for this historical run.</p>
      ) : (
        <pre>
          {JSON.stringify(
            snapshot,
            null,
            2,
          )}
        </pre>
      )}
    </article>
  );
}

function CopyValue({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  function copy() {
    void navigator.clipboard?.writeText(
      value,
    );
  }

  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <button
        type="button"
        className="button secondary"
        aria-label={`Copy ${label.toLowerCase()}`}
        onClick={copy}
      >
        Copy
      </button>
    </div>
  );
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
  ].some((snapshot) => snapshot === null);
}

export function ReproducibilityExperience({
  state,
  workspaceId,
  projectId,
  analysisRunId,
  resultAvailable = false,
  reportsAvailable = false,
}: {
  workspaceId?: string;
  projectId?: string;
  analysisRunId?: string;
  resultAvailable?: boolean;
  reportsAvailable?: boolean;
  state: AnalysisLineageState;
}) {
  if (state.kind === "loading") {
    return (
      <main className="state-shell">
        <section className="state-card">
          <p className="eyebrow">
            Reproducibility
          </p>
          <h1>
            Loading reproducibility lineage
          </h1>
        </section>
      </main>
    );
  }

  if (state.kind === "permission") {
    return (
      <main className="state-shell">
        <section className="state-card">
          <p className="eyebrow">
            Reproducibility
          </p>
          <h1>
            You don’t have access to this lineage
          </h1>
        </section>
      </main>
    );
  }

  if (state.kind === "missing") {
    return (
      <main className="state-shell">
        <section className="state-card">
          <p className="eyebrow">
            Reproducibility
          </p>
          <h1>
            Reproducibility lineage was not found
          </h1>
        </section>
      </main>
    );
  }

  if (state.kind === "error") {
    return (
      <main className="state-shell">
        <section className="state-card">
          <p className="eyebrow">
            Reproducibility
          </p>
          <h1>
            Reproducibility details are temporarily unavailable
          </h1>
        </section>
      </main>
    );
  }

  const data = state.data;
  const legacy = isLegacy(data);

  const libraries = Object.entries(
    data.statistical_library_versions ?? {},
  ).sort(([left], [right]) =>
    left.localeCompare(right),
  );

  return (
    <main className="results-shell">
      <section className="conclusion trusted">
        <div>
          <p className="eyebrow">
            Read-only execution receipt
          </p>

          <h1>
            Reproducibility and lineage
          </h1>

          <p className="confidence-copy">
            This view shows the persisted inputs
            and software lineage captured for this
            analysis run.
          </p>
        </div>
      </section>

      {legacy ? (
        <section className="warning-panel">
          <p className="eyebrow">
            Legacy run
          </p>
          <h2>
            Some lineage fields are unavailable for this historical run.
          </h2>
        </section>
      ) : null}

            {workspaceId && projectId && analysisRunId ? (
        <nav
          className="state-actions"
          aria-label="Analysis run navigation"
        >
          <Link
            className="button secondary"
            href={analysisRunPath(
              workspaceId,
              projectId,
              analysisRunId,
            )}
          >
            View Analysis Status
          </Link>

          {resultAvailable ? (
            <Link
              className="button secondary"
              href={analysisResultPath(
                workspaceId,
                projectId,
                analysisRunId,
              )}
            >
              View Results
            </Link>
          ) : null}

          {reportsAvailable ? (
            <Link
              className="button secondary"
              href={`${analysisRunPath(
                workspaceId,
                projectId,
                analysisRunId,
              )}/reports`}
            >
              View Reports
            </Link>
          ) : null}
        </nav>
      ) : null}

<section className="panel">
        <p className="eyebrow">
          Reproducibility boundary
        </p>
        <p>
          Matching lineage captures the immutable inputs, random seed,
          application version, source revision, and statistical library
          versions used for this analysis. It does not guarantee bit-for-bit
          identical results across different hardware, operating systems or
          numerical backends.
        </p>
      </section>

      <section
        className="metric-grid"
        aria-label="Reproducibility identifiers"
      >
        <CopyValue
          label="Input fingerprint"
          value={
            data.input_fingerprint_sha256
          }
        />

        <CopyValue
          label="Dataset checksum"
          value={
            data.dataset_checksum_sha256
          }
        />

        <CopyValue
          label="Source revision"
          value={data.source_revision}
        />
      </section>

      <section className="metric-grid">
        <div className="metric">
          <span>Estimator</span>
          <strong>
            {data.estimator_type}
          </strong>
        </div>

        <div className="metric">
          <span>Estimator version</span>
          <strong>
            {data.estimator_version}
          </strong>
        </div>

        <div className="metric">
          <span>Random seed</span>
          <strong>
            {data.random_seed}
          </strong>
        </div>

        <div className="metric">
          <span>Application version</span>
          <strong>
            {data.application_version}
          </strong>
        </div>
      </section>

      <section className="panel">
        <p className="eyebrow">
          Estimand
        </p>

        {data.estimand_snapshot === null ? (
          <p>
            Unavailable for this historical run.
          </p>
        ) : (
          <div className="technical-grid">
            <div className="metric">
              <span>Estimand type</span>
              <strong>
                {value(
                  data.estimand_snapshot,
                  "estimand_type",
                )}
              </strong>
            </div>

            <div className="metric">
              <span>Target outcome</span>
              <strong>
                {value(
                  data.estimand_snapshot,
                  "target_outcome",
                )}
              </strong>
            </div>

            <div className="metric">
              <span>Target population</span>
              <strong>
                {value(
                  data.estimand_snapshot,
                  "target_population",
                )}
              </strong>
            </div>

            <div className="metric">
              <span>Effect scale</span>
              <strong>
                {value(
                  data.estimand_snapshot,
                  "effect_scale",
                )}
              </strong>
            </div>
          </div>
        )}
      </section>

      <section className="panel">
        <p className="eyebrow">
          Statistical libraries
        </p>

        {libraries.length === 0 ? (
          <p>
            No persisted statistical library versions are available.
          </p>
        ) : (
          <ul>
            {libraries.map(
              ([name, version]) => (
                <li key={name}>
                  {name} {version}
                </li>
              ),
            )}
          </ul>
        )}
      </section>

      <section className="story-grid">
        <Snapshot
          title="Semantic mapping snapshot"
          snapshot={
            data.semantic_mapping_snapshot
          }
        />

        <Snapshot
          title="Analysis period snapshot"
          snapshot={
            data.analysis_period_snapshot
          }
        />

        <Snapshot
          title="Analysis selection snapshot"
          snapshot={
            data.analysis_selection_snapshot
          }
        />

        <Snapshot
          title="Treatment and control snapshot"
          snapshot={
            data.treatment_control_snapshot
          }
        />
      </section>

      <details className="technical">
        <summary>
          Full persisted lineage
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
