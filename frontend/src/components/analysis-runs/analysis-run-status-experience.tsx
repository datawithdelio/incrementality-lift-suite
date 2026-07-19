"use client";

import Link from "next/link";

import {
  analysisResultPath,
  analysisRunPath,
} from "@/lib/projects/routes";
import type {
  ResultsState,
} from "@/lib/results/types";

import {
  StatusState,
} from "@/components/results/status-state";

export function AnalysisRunStatusExperience({
  state,
}: {
  state: ResultsState;
}) {
  if (state.kind === "loading") {
    return (
      <main className="state-shell">
        <section
          className="state-card"
          aria-live="polite"
          aria-busy="true"
        >
          <p className="eyebrow">
            Analysis status
          </p>
          <h1>
            Loading analysis status
          </h1>
          <p>
            Checking the latest status from the server.
          </p>
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

  const {
    data,
    refreshError,
  } = state;

  const runPath =
    analysisRunPath(
      data.workspace_id,
      data.project_id,
      data.analysis_run_id,
    );

  if (
    data.lifecycle_status
    === "failed"
  ) {
    return (
      <main className="state-shell">
        <section
          className="state-card"
          aria-live="polite"
        >
          <p className="eyebrow">
            Failed
          </p>

          <h1>
            Analysis failed
          </h1>

          <p
            role="alert"
          >
            {
              data.failure_information
              ?? "Analysis could not be completed. Review the configuration and try again."
            }
          </p>

          {data.attempt_count > 0 ? (
            <p className="attempt">
              Attempt {data.attempt_count} of {data.max_attempts}
            </p>
          ) : null}

          <div className="state-actions">
            <Link
              className="button secondary"
              href={`${runPath}/lineage`}
            >
              View Reproducibility
            </Link>
          </div>
        </section>
      </main>
    );
  }

  if (
    data.lifecycle_status
    === "succeeded"
  ) {
    return (
      <>
        <main className="state-shell">
          <section
            className="state-card"
            aria-live="polite"
          >
            <p className="eyebrow">
              Complete
            </p>

            <h1>
              Analysis complete
            </h1>

            <p>
              {data.result
                ? "Your analysis finished successfully and the result is available."
                : "Your analysis finished successfully. The result is still becoming available."}
            </p>

            <div className="state-actions">
              {data.result ? (
                <Link
                  className="button"
                  href={analysisResultPath(
                    data.workspace_id,
                    data.project_id,
                    data.analysis_run_id,
                  )}
                >
                  View Results
                </Link>
              ) : null}

              <Link
                className="button secondary"
                href={`${runPath}/lineage`}
              >
                View Reproducibility
              </Link>
            </div>
          </section>
        </main>

        <AnalysisRunSummary
          estimatorType={data.estimator_type}
          configuration={
            data.analysis_configuration
          }
          datasetId={data.dataset_id}
          semanticMappingVersion={
            data.semantic_mapping_version
          }
          createdAt={data.created_at}
          startedAt={data.started_at}
          completedAt={data.completed_at}
        />
      </>
    );
  }

  return (
    <>
      {refreshError ? (
        <div
          role="alert"
          className="status-refresh-alert"
        >
          Unable to refresh analysis status.
          Showing the last known status.
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

      <AnalysisRunSummary
        estimatorType={data.estimator_type}
        configuration={
          data.analysis_configuration
        }
        datasetId={data.dataset_id}
        semanticMappingVersion={
          data.semantic_mapping_version
        }
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
}: {
  estimatorType: string;
  configuration: Record<
    string,
    unknown
  >;
  datasetId?: string;
  semanticMappingVersion?: number;
  createdAt?: string;
  startedAt?: string | null;
  completedAt?: string | null;
}) {
  const estimatorLabel =
    estimatorType
      .replaceAll("_", " ")
      .replace(
        /^./,
        (character) =>
          character.toUpperCase(),
      );

  const analysisStart =
    configuration
      .analysis_start_date;

  const analysisEnd =
    configuration
      .analysis_end_date;

  const intervention =
    configuration
      .intervention_date;

  return (
    <section
      className="state-card"
      aria-labelledby="analysis-run-summary-heading"
    >
      <p className="eyebrow">
        Run configuration
      </p>

      <h2
        id="analysis-run-summary-heading"
      >
        Analysis summary
      </h2>

      <dl>
        {datasetId ? (
          <div>
            <dt>
              Dataset
            </dt>
            <dd>
              {datasetId}
            </dd>
          </div>
        ) : null}

        {typeof semanticMappingVersion === "number" ? (
          <div>
            <dt>
              Semantic mapping
            </dt>
            <dd>
              Mapping version {semanticMappingVersion}
            </dd>
          </div>
        ) : null}

        {createdAt ? (
          <div>
            <dt>
              Queued
            </dt>
            <dd>
              {formatTimestamp(createdAt)}
            </dd>
          </div>
        ) : null}

        {startedAt ? (
          <div>
            <dt>
              Started
            </dt>
            <dd>
              {formatTimestamp(startedAt)}
            </dd>
          </div>
        ) : null}

        {completedAt ? (
          <div>
            <dt>
              Completed
            </dt>
            <dd>
              {formatTimestamp(completedAt)}
            </dd>
          </div>
        ) : null}

        <div>
          <dt>
            Estimator
          </dt>
          <dd>
            {estimatorLabel}
          </dd>
        </div>

        {typeof analysisStart === "string" ? (
          <div>
            <dt>
              Analysis start
            </dt>
            <dd>
              {analysisStart}
            </dd>
          </div>
        ) : null}

        {typeof analysisEnd === "string" ? (
          <div>
            <dt>
              Analysis end
            </dt>
            <dd>
              {analysisEnd}
            </dd>
          </div>
        ) : null}

        {typeof intervention === "string" ? (
          <div>
            <dt>
              Intervention date
            </dt>
            <dd>
              {intervention}
            </dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}

function formatTimestamp(
  value: string,
): string {
  return new Date(value).toLocaleString(
    "en-US",
    {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZone: "UTC",
    },
  );
}

function StatusMessage({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <main className="state-shell">
      <section className="state-card">
        <p className="eyebrow">
          Analysis status
        </p>
        <h1>
          {title}
        </h1>
        <p>
          {body}
        </p>
      </section>
    </main>
  );
}
