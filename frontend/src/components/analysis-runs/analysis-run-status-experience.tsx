"use client";

import Link from "next/link";

import { analysisResultPath, analysisRunPath } from "@/lib/projects/routes";
import type { ResultsState } from "@/lib/results/types";

import { StatusState } from "@/components/results/status-state";

export function AnalysisRunStatusExperience({
  state,
}: {
  state: ResultsState;
}) {
  if (state.kind === "loading") {
    return (
      <main className="state-shell">
        <section className="state-card" aria-live="polite" aria-busy="true">
          <p className="eyebrow">Analysis status</p>
          <h1>Loading analysis status</h1>
          <p>Checking the latest status from the server.</p>
        </section>
      </main>
    );
  }

  if (state.kind === "permission") {
    return (
      <StatusMessage
        title="You don’t have access to this analysis"
        body="Ask a workspace administrator for access, or switch to the correct workspace."
      />
    );
  }

  if (state.kind === "missing") {
    return (
      <StatusMessage
        title="We couldn’t find this analysis"
        body="It may have been removed or belong to another project."
      />
    );
  }

  if (state.kind === "error") {
    return (
      <StatusMessage
        title="Analysis status is temporarily unavailable"
        body="Refresh the page to try again. The analysis continues independently on the server."
      />
    );
  }

  const { data, refreshError } = state;

  const runPath = analysisRunPath(
    data.workspace_id,
    data.project_id,
    data.analysis_run_id,
  );

  if (data.lifecycle_status === "failed") {
    return (
      <main className="state-shell">
        <section className="state-card" aria-live="polite">
          <p className="eyebrow">Failed</p>

          <h1>Analysis failed</h1>

          <p role="alert">
            {data.failure_information ??
              "Analysis could not be completed. Review the configuration and try again."}
          </p>

          {data.attempt_count > 0 ? (
            <p className="attempt">
              Attempt {data.attempt_count} of {data.max_attempts}
            </p>
          ) : null}

          <div className="state-actions">
            <Link className="button secondary" href={`${runPath}/lineage`}>
              View Reproducibility
            </Link>
          </div>
        </section>
      </main>
    );
  }

  if (data.lifecycle_status === "succeeded") {
    return (
      <main className="analysis-complete-shell">
        <section
          className="analysis-complete-card"
          aria-live="polite"
          aria-labelledby="analysis-complete-heading"
        >
          <div className="analysis-complete-celebration" aria-hidden="true">
            <span className="analysis-complete-confetti confetti-one" />
            <span className="analysis-complete-confetti confetti-two" />
            <span className="analysis-complete-confetti confetti-three" />
            <span className="analysis-complete-confetti confetti-four" />
            <span className="analysis-complete-confetti confetti-five" />

            <span className="analysis-complete-success-icon">
              <i />
            </span>
          </div>

          <p className="analysis-complete-eyebrow">Complete</p>

          <h1 id="analysis-complete-heading">Analysis complete</h1>

          <p className="analysis-complete-description">
            {data.result
              ? "Your analysis finished successfully and the result is available."
              : "Your analysis finished successfully. The result is still becoming available."}
          </p>

          <div
            className={`analysis-complete-actions ${
              data.result ? "" : "is-single"
            }`}
          >
            {data.result ? (
              <Link
                className="analysis-complete-action is-primary"
                href={analysisResultPath(
                  data.workspace_id,
                  data.project_id,
                  data.analysis_run_id,
                )}
              >
                <span
                  className="analysis-complete-action-icon results-icon"
                  aria-hidden="true"
                >
                  <i />
                  <i />
                  <i />
                </span>
                View Results
              </Link>
            ) : null}

            <Link
              className="analysis-complete-action is-secondary"
              href={`${runPath}/lineage`}
            >
              <span
                className="analysis-complete-action-icon lineage-icon"
                aria-hidden="true"
              >
                <i />
                <i />
                <i />
              </span>
              View Reproducibility
            </Link>
          </div>

          <AnalysisRunSummary
            embedded
            estimatorType={data.estimator_type}
            configuration={data.analysis_configuration}
            datasetId={data.dataset_id}
            semanticMappingVersion={data.semantic_mapping_version}
            createdAt={data.created_at}
            startedAt={data.started_at}
            completedAt={data.completed_at}
          />
        </section>
      </main>
    );
  }

  return (
    <>
      {refreshError ? (
        <div role="alert" className="status-refresh-alert">
          Unable to refresh analysis status. Showing the last known status.
        </div>
      ) : null}

      <StatusState
        status={data.lifecycle_status}
        attempt={
          data.attempt_count
            ? `Attempt ${data.attempt_count} of ${data.max_attempts}`
            : undefined
        }
      />

      <div className="state-actions">
        <Link className="button secondary" href={`${runPath}/lineage`}>
          View Reproducibility
        </Link>
      </div>

      <AnalysisRunSummary
        estimatorType={data.estimator_type}
        configuration={data.analysis_configuration}
        datasetId={data.dataset_id}
        semanticMappingVersion={data.semantic_mapping_version}
        createdAt={data.created_at}
        startedAt={data.started_at}
        completedAt={data.completed_at}
      />
    </>
  );
}

function AnalysisRunSummary({
  estimatorType,
  configuration,
  datasetId,
  semanticMappingVersion,
  createdAt,
  startedAt,
  completedAt,
  embedded = false,
}: {
  estimatorType: string;
  configuration: Record<string, unknown>;
  datasetId?: string;
  semanticMappingVersion?: number;
  createdAt?: string;
  startedAt?: string | null;
  completedAt?: string | null;
  embedded?: boolean;
}) {
  const estimatorLabel = estimatorType
    .replaceAll("_", " ")
    .replace(/^./, (character) => character.toUpperCase());

  const analysisStart =
    typeof configuration.analysis_start_date === "string"
      ? configuration.analysis_start_date
      : null;

  const analysisEnd =
    typeof configuration.analysis_end_date === "string"
      ? configuration.analysis_end_date
      : null;

  const intervention =
    typeof configuration.intervention_date === "string"
      ? configuration.intervention_date
      : null;

  const analysisPeriod =
    analysisStart || analysisEnd
      ? `${analysisStart ? formatRunDate(analysisStart) : "Not specified"} – ${
          analysisEnd ? formatRunDate(analysisEnd) : "Not specified"
        }`
      : "Not specified";

  const duration = formatRunDuration(startedAt, completedAt);

  if (embedded) {
    return (
      <section
        className="analysis-complete-summary"
        aria-labelledby="analysis-run-summary-heading"
      >
        <span className="analysis-complete-sr-only">Run configuration</span>

        <span className="analysis-complete-sr-only">Analysis summary</span>

        <h2 id="analysis-run-summary-heading" aria-label="Analysis summary">
          Run summary
        </h2>

        <dl className="analysis-complete-summary-grid">
          {datasetId ? (
            <div className="analysis-complete-summary-dataset">
              <dt>Dataset</dt>
              <dd title={datasetId}>{datasetId}</dd>

              {typeof semanticMappingVersion === "number" ? (
                <small>{`Mapping version ${semanticMappingVersion}`}</small>
              ) : null}
            </div>
          ) : null}

          <div>
            <dt>Analysis</dt>
            <dd>{estimatorLabel}</dd>
          </div>

          <div>
            <dt>Intervention date</dt>
            <dd>
              {intervention ? formatRunDate(intervention) : "Not specified"}
            </dd>
          </div>

          <div>
            <dt>Analysis period</dt>
            <dd>{analysisPeriod}</dd>
          </div>
        </dl>

        <div className="analysis-complete-summary-timing">
          {createdAt ? (
            <div>
              <span>Queued</span>
              <strong>{formatTimestamp(createdAt)}</strong>
            </div>
          ) : null}

          {startedAt ? (
            <div>
              <span>Started</span>
              <strong>{formatTimestamp(startedAt)}</strong>
            </div>
          ) : null}

          {completedAt ? (
            <div>
              <span>Completed</span>
              <strong>{formatTimestamp(completedAt)}</strong>
            </div>
          ) : null}

          {duration ? (
            <div>
              <span>Duration</span>
              <strong>{duration}</strong>
            </div>
          ) : null}
        </div>
      </section>
    );
  }

  return (
    <section
      className="state-card analysis-run-summary-card"
      aria-labelledby="analysis-run-summary-heading"
    >
      <p className="eyebrow">Run configuration</p>

      <h2 id="analysis-run-summary-heading">Analysis summary</h2>

      <dl className="analysis-run-summary-list">
        {datasetId ? (
          <div>
            <dt>Dataset</dt>
            <dd>{datasetId}</dd>
          </div>
        ) : null}

        {typeof semanticMappingVersion === "number" ? (
          <div>
            <dt>Semantic mapping</dt>
            <dd>Mapping version {semanticMappingVersion}</dd>
          </div>
        ) : null}

        {createdAt ? (
          <div>
            <dt>Queued</dt>
            <dd>{formatTimestamp(createdAt)}</dd>
          </div>
        ) : null}

        {startedAt ? (
          <div>
            <dt>Started</dt>
            <dd>{formatTimestamp(startedAt)}</dd>
          </div>
        ) : null}

        {completedAt ? (
          <div>
            <dt>Completed</dt>
            <dd>{formatTimestamp(completedAt)}</dd>
          </div>
        ) : null}

        <div>
          <dt>Estimator</dt>
          <dd>{estimatorLabel}</dd>
        </div>

        {analysisStart ? (
          <div>
            <dt>Analysis start</dt>
            <dd>{analysisStart}</dd>
          </div>
        ) : null}

        {analysisEnd ? (
          <div>
            <dt>Analysis end</dt>
            <dd>{analysisEnd}</dd>
          </div>
        ) : null}

        {intervention ? (
          <div>
            <dt>Intervention date</dt>
            <dd>{intervention}</dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}

function formatRunDate(value: string): string {
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? new Date(`${value}T00:00:00`)
    : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function formatRunDuration(
  startedAt?: string | null,
  completedAt?: string | null,
): string | null {
  if (!startedAt || !completedAt) {
    return null;
  }

  const started = Date.parse(startedAt);
  const completed = Date.parse(completedAt);

  if (Number.isNaN(started) || Number.isNaN(completed) || completed < started) {
    return null;
  }

  const totalSeconds = Math.floor((completed - started) / 1000);

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return [hours, minutes, seconds]
    .map((part) => String(part).padStart(2, "0"))
    .join(":");
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

function StatusMessage({ title, body }: { title: string; body: string }) {
  return (
    <main className="state-shell">
      <section className="state-card">
        <p className="eyebrow">Analysis status</p>
        <h1>{title}</h1>
        <p>{body}</p>
      </section>
    </main>
  );
}
