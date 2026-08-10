"use client";

import { useState } from "react";

import { ArrowRight, WarningCircle } from "@phosphor-icons/react";

import { useRouter } from "next/navigation";

import { SESSION_TOKEN_KEY } from "@/lib/auth/api";

import {
  AnalysisRunApiError,
  humanizeAnalysisRunQueueError,
  queueAnalysisRun,
} from "@/lib/analysis-configuration/api";

import {
  mapAnalysisConfigurationRequest,
  type AnalysisConfigurationDraft,
  type FilterOperator,
  type OffPolicyMethod,
} from "@/lib/analysis-configuration/request";

import {
  analysisConfigurationPath,
  analysisRunPath,
  projectPath,
} from "@/lib/projects/routes";

type MappingTreatment = {
  column: string | null;
  treatmentValue: string | null;
  controlValue: string | null;
};

type Props = {
  draft: AnalysisConfigurationDraft;
  mappingTreatment: MappingTreatment;

  workspaceId: string;
  projectId: string;

  datasetId: string;
  semanticMappingVersion: number;
};

type RecoveryAction = {
  href: string;
  label: string;
};

type SubmissionFailure = {
  message: string;
  recoveryAction: RecoveryAction | null;
};

function queueRecoveryAction(
  error: unknown,
  workspaceId: string,
  projectId: string,
): RecoveryAction | null {
  if (!(error instanceof AnalysisRunApiError)) {
    return null;
  }

  switch (error.status) {
    case 401:
      return {
        href: "/login",
        label: "Sign in again",
      };

    case 404:
      return {
        href: projectPath(workspaceId, projectId),
        label: "Review latest project data",
      };

    case 409:
      return {
        href: analysisConfigurationPath(workspaceId, projectId),
        label: "Restart with latest data",
      };

    case 422:
      return {
        href: analysisConfigurationPath(workspaceId, projectId),
        label: "Review configuration",
      };

    default:
      return null;
  }
}

const ESTIMATOR_LABELS = {
  difference_in_differences: "Difference in Differences",

  synthetic_control: "Synthetic Control",

  geo_holdout: "Geo Holdout",

  marketing_mix_model: "Marketing Mix Modeling",

  off_policy_evaluation: "Off-policy Evaluation",
} satisfies Record<AnalysisConfigurationDraft["estimatorType"], string>;

const OPERATOR_LABELS = {
  equals: "Equals",
  not_equals: "Not equals",
  contains: "Contains",

  greater_than: "Greater than",

  greater_than_or_equal: "Greater than or equal",

  less_than: "Less than",

  less_than_or_equal: "Less than or equal",

  is_null: "Is null",

  is_not_null: "Is not null",
} satisfies Record<FilterOperator, string>;

const OFF_POLICY_METHOD_LABELS = {
  importance_sampling: "Importance sampling",

  self_normalized_importance_sampling: "Self-normalized importance sampling",

  doubly_robust: "Doubly robust",
} satisfies Record<OffPolicyMethod, string>;

function displayValue(value: string | null): string {
  if (value === null || value.trim().length === 0) {
    return "Not configured";
  }

  return value;
}

function displayList(values: string[]): string {
  if (values.length === 0) {
    return "None";
  }

  return values.join(", ");
}

export function AnalysisConfigurationReview({
  draft,
  mappingTreatment,
  workspaceId,
  projectId,
  datasetId,
  semanticMappingVersion,
}: Props) {
  const router = useRouter();

  const [isSubmitting, setIsSubmitting] = useState(false);

  const [submissionFailure, setSubmissionFailure] =
    useState<SubmissionFailure | null>(null);

  const request = mapAnalysisConfigurationRequest(draft, {
    datasetId,
    semanticMappingVersion,
  });

  async function handleQueueAnalysis(): Promise<void> {
    if (isSubmitting) {
      return;
    }

    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);

    if (!token) {
      setSubmissionFailure({
        message: "Your session has expired. " + "Sign in again and retry.",
        recoveryAction: {
          href: "/login",
          label: "Sign in again",
        },
      });

      return;
    }

    setIsSubmitting(true);
    setSubmissionFailure(null);

    try {
      const run = await queueAnalysisRun(
        token,
        workspaceId,
        projectId,
        request,
      );

      router.push(analysisRunPath(workspaceId, projectId, run.id));

      // Navigation is in progress. Keep the
      // action disabled so a second run cannot
      // be queued accidentally.
    } catch (error) {
      setSubmissionFailure({
        message: humanizeAnalysisRunQueueError(error),
        recoveryAction: queueRecoveryAction(error, workspaceId, projectId),
      });

      setIsSubmitting(false);
    }
  }

  return (
    <main className="analysis-review-shell">
      <header className="analysis-review-hero">
        <p className="analysis-review-hero__eyebrow">Final review</p>

        <h1>Configure Analysis</h1>

        <p>
          Confirm the exact dataset, population, estimator, and settings before
          the analysis run is queued.
        </p>
      </header>

      <section
        className="analysis-review-card"
        aria-labelledby={"review-analysis-heading"}
      >
        <header className="analysis-review-card__header">
          <span className="analysis-review-card__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="m7 12 3 3 7-7M6 3h9l3 3v15H6V3Z"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>

          <span>
            <h2 id={"review-analysis-heading"}>
              Review analysis configuration
            </h2>

            <p>Everything below will be preserved with the queued run.</p>
          </span>

          <span className="analysis-review-status">
            <span aria-hidden="true">✓</span>
            Ready to queue
          </span>
        </header>

        <div className="analysis-review-content">
          <section
            className="analysis-review-overview"
            aria-label="Analysis overview"
          >
            <article>
              <small>Method</small>

              <strong>{ESTIMATOR_LABELS[draft.estimatorType]}</strong>

              <span>Estimator selected for this analysis</span>
            </article>

            <article>
              <small>Analysis period</small>

              <strong>
                {draft.period.analysisStartDate}
                {" → "}
                {draft.period.analysisEndDate}
              </strong>

              <span>
                {draft.period.interventionDate !== null
                  ? `Intervention: ${draft.period.interventionDate}`
                  : "No intervention date required"}
              </span>
            </article>

            <article>
              <small>Dataset snapshot</small>

              <strong>{datasetId}</strong>

              <span>Exact dataset associated with the run</span>
            </article>

            <article>
              <small>Mapping version</small>

              <strong>Version {semanticMappingVersion}</strong>

              <span>Saved semantic definition</span>
            </article>
          </section>

          <div className="analysis-review-grid">
            <section className="analysis-review-section">
              <header>
                <span
                  className="analysis-review-section__number"
                  aria-hidden="true"
                >
                  1
                </span>

                <span>
                  <h3>Population filters</h3>

                  <p>Rules applied before estimation.</p>
                </span>

                <span className="analysis-review-section__count">
                  {draft.selection.rowFilters.length}{" "}
                  {draft.selection.rowFilters.length === 1
                    ? "filter"
                    : "filters"}
                </span>
              </header>

              <div className="analysis-review-section__body">
                {draft.selection.rowFilters.length === 0 ? (
                  <p className="analysis-review-empty">No filters applied.</p>
                ) : (
                  <ul className="analysis-review-pill-list">
                    {draft.selection.rowFilters.map((rule, index) => (
                      <li key={[rule.column, rule.operator, index].join("-")}>
                        {rule.column}
                        {" · "}
                        {OPERATOR_LABELS[rule.operator]}

                        {rule.value === undefined
                          ? ""
                          : ` · ${String(rule.value.value)}`}
                      </li>
                    ))}
                  </ul>
                )}

                <dl className="analysis-review-details">
                  {draft.treatmentControl.kind !== "off_policy_evaluation" && (

                    <>

                      <div>

                        <dt>Included geographies</dt>


                        <dd>{displayList(draft.selection.selectedGeographies)}</dd>

                      </div>


                      <div>

                        <dt>Excluded geographies</dt>


                        <dd>{displayList(draft.selection.excludedGeographies)}</dd>

                      </div>

                    </>

                  )}

                  {draft.selection.segmentColumn.trim().length > 0 && (
                    <>
                      <div>
                        <dt>Segment column</dt>

                        <dd>{draft.selection.segmentColumn}</dd>
                      </div>

                      <div>
                        <dt>Included segments</dt>

                        <dd>{displayList(draft.selection.selectedSegments)}</dd>
                      </div>

                      <div>
                        <dt>Excluded segments</dt>

                        <dd>{displayList(draft.selection.excludedSegments)}</dd>
                      </div>
                    </>
                  )}
                </dl>
              </div>
            </section>

            <section className="analysis-review-section">
              <header>
                <span
                  className="analysis-review-section__number"
                  aria-hidden="true"
                >
                  2
                </span>

                <span>
                  <h3>
                    {draft.treatmentControl.kind === "off_policy_evaluation"
                      ? "Policy assignment"
                      : "Treatment and control"}
                  </h3>

                  <p>Comparison design used by the estimator.</p>
                </span>
              </header>

              <div className="analysis-review-section__body">
                {draft.treatmentControl.kind === "mapped_binary" && (
                  <dl className="analysis-review-details">
                    <div>
                      <dt>Treatment column</dt>

                      <dd>
                        Treatment column:{" "}
                        {displayValue(mappingTreatment.column)}
                      </dd>
                    </div>

                    <div data-tone="treated">
                      <dt>Treated value</dt>

                      <dd>
                        Treatment value:{" "}
                        {displayValue(mappingTreatment.treatmentValue)}
                      </dd>
                    </div>

                    <div data-tone="control">
                      <dt>Control value</dt>

                      <dd>
                        Control value:{" "}
                        {displayValue(mappingTreatment.controlValue)}
                      </dd>
                    </div>
                  </dl>
                )}

                {draft.treatmentControl.kind === "synthetic_control" && (
                  <dl className="analysis-review-details">
                    <div data-tone="treated">
                      <dt>Treated unit</dt>

                      <dd>
                        Treated unit: {draft.treatmentControl.treatedUnit}
                      </dd>
                    </div>

                    <div data-tone="control">
                      <dt>Donor pool</dt>

                      <dd>
                        Donor pool:{" "}
                        {displayList(draft.treatmentControl.donorPool)}
                      </dd>
                    </div>
                  </dl>
                )}

                {draft.treatmentControl.kind === "geo_holdout" && (
                  <dl className="analysis-review-details">
                    <div data-tone="treated">
                      <dt>Treated geographies</dt>

                      <dd>
                        Treated geographies:{" "}
                        {displayList(draft.treatmentControl.treatedGeographies)}
                      </dd>
                    </div>

                    <div data-tone="control">
                      <dt>Control geographies</dt>

                      <dd>
                        Control geographies:{" "}
                        {displayList(draft.treatmentControl.controlGeographies)}
                      </dd>
                    </div>
                  </dl>
                )}

                {draft.treatmentControl.kind === "not_applicable" && (
                  <p className="analysis-review-empty">
                    No treatment or control assignment is required.
                  </p>
                )}

                {draft.treatmentControl.kind === "off_policy_evaluation" && (
                  <dl className="analysis-review-details">
                    <div>
                      <dt>Policy</dt>

                      <dd>Policy: {draft.treatmentControl.policyName}</dd>
                    </div>

                    <div>
                      <dt>Behavior propensity</dt>

                      <dd>
                        Behavior propensity column:{" "}
                        {draft.treatmentControl.behaviorPropensityColumn}
                      </dd>
                    </div>

                    <div>
                      <dt>Target propensity</dt>

                      <dd>
                        Target propensity column:{" "}
                        {draft.treatmentControl.targetPropensityColumn}
                      </dd>
                    </div>
                  </dl>
                )}
              </div>
            </section>

            <section className="analysis-review-section analysis-review-section--wide">
              <header>
                <span
                  className="analysis-review-section__number"
                  aria-hidden="true"
                >
                  3
                </span>

                <span>
                  <h3>Estimator settings</h3>

                  <p>Method-specific inputs used during execution.</p>
                </span>
              </header>

              <div className="analysis-review-section__body">
                {draft.settings.kind === "difference_in_differences" && (
                  <p className="analysis-review-empty">
                    No additional Difference in Differences settings are
                    required. did-v1 is unadjusted; mapped covariates are retained
                    in lineage but are not included in the fitted model.
                  </p>
                )}

                {draft.settings.kind === "synthetic_control" && (
                  <p className="analysis-review-empty">
                    The treated unit and donor pool fully define the Synthetic
                    Control settings.
                  </p>
                )}

                {draft.settings.kind === "geo_holdout" && (
                  <dl className="analysis-review-details analysis-review-details--columns">
                    <div>
                      <dt>Outcome kind</dt>

                      <dd>{draft.settings.outcomeKind}</dd>
                    </div>

                    <div>
                      <dt>Coordinate coverage</dt>

                      <dd>
                        {Object.keys(draft.settings.coordinates).length}{" "}
                        geographies
                      </dd>
                    </div>
                  </dl>
                )}

                {draft.settings.kind === "marketing_mix_model" && (
                  <dl className="analysis-review-details analysis-review-details--columns">
                    <div>
                      <dt>Outcome kind</dt>

                      <dd>{draft.settings.outcomeKind}</dd>
                    </div>

                    <div>
                      <dt>Seasonality period</dt>

                      <dd>{draft.settings.seasonalityPeriod}</dd>
                    </div>

                    <div>
                      <dt>Configured channels</dt>

                      <dd>{Object.keys(draft.settings.adstockDecay).length}</dd>
                    </div>
                  </dl>
                )}

                {draft.settings.kind === "off_policy_evaluation" && (
                  <dl className="analysis-review-details analysis-review-details--columns">
                    <div>
                      <dt>Reward column</dt>

                      <dd>{draft.settings.rewardColumn}</dd>
                    </div>

                    <div>
                      <dt>Observed-action expected reward column</dt>

                      <dd>
                        {draft.settings.observedActionExpectedRewardColumn}
                      </dd>
                    </div>

                    <div>
                      <dt>Target-policy expected reward column</dt>

                      <dd>
                        {draft.settings.targetPolicyExpectedRewardColumn}
                      </dd>
                    </div>

                    <div>
                      <dt>Primary method</dt>

                      <dd>
                        {OFF_POLICY_METHOD_LABELS[draft.settings.primaryMethod]}
                      </dd>
                    </div>
                  </dl>
                )}
              </div>
            </section>
          </div>

          <details className="analysis-review-request">
            <summary>
              <span
                className="analysis-review-request__icon"
                aria-hidden="true"
              >
                {"{ }"}
              </span>

              <span>
                <strong>Exact queue request</strong>

                <small>
                  Technical payload preserved with the analysis run.
                </small>
              </span>

              <span
                className="analysis-review-request__caret"
                aria-hidden="true"
              >
                ⌄
              </span>
            </summary>

            <pre>{JSON.stringify(request, null, 2)}</pre>
          </details>

          <div className="analysis-review-confirmation">
            <span aria-hidden="true">✓</span>

            <p>
              <strong>Configuration checks complete</strong>

              <small>
                Queueing creates one immutable analysis run from this exact
                dataset and mapping snapshot.
              </small>
            </p>
          </div>

          {submissionFailure !== null && (
            <div
              className="analysis-queue-error analysis-review-queue-error"
              role="alert"
              aria-live="assertive"
            >
              <WarningCircle size={22} weight="fill" aria-hidden="true" />

              <div>
                <strong>Analysis not queued</strong>

                <p>{submissionFailure.message}</p>

                {submissionFailure.recoveryAction !== null && (
                  <a href={submissionFailure.recoveryAction.href}>
                    {submissionFailure.recoveryAction.label}

                    <ArrowRight size={17} aria-hidden="true" />
                  </a>
                )}
              </div>
            </div>
          )}
        </div>

        <footer className="analysis-review-actions">
          <span>
            <strong>
              {isSubmitting
                ? "Creating analysis run"
                : "Ready to create analysis run"}
            </strong>

            <small>
              {isSubmitting
                ? "Your configuration is being queued. Keep this page open."
                : "The next screen will show execution status and progress."}
            </small>
          </span>

          <button
            type="button"
            disabled={isSubmitting}
            aria-busy={isSubmitting}
            onClick={() => {
              void handleQueueAnalysis();
            }}
          >
            {isSubmitting ? "Queueing analysis…" : "Queue analysis"}

            {!isSubmitting && <ArrowRight size={18} aria-hidden="true" />}
          </button>
        </footer>
      </section>
    </main>
  );
}
