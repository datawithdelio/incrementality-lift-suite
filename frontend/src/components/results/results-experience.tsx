"use client";

import type { ResultsState } from "@/lib/results/types";
import Link from "next/link";

import { ComparisonChart, EventStudyChart } from "./result-charts";
import { GeoHoldoutPanels, MarketingMixPanels, OffPolicyEvaluationPanels, SyntheticControlPanels } from "./estimator-result-panels";
import { StatusState } from "./status-state";

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function arrayValue(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object")) : [];
}
function stringArray(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []; }
function number(value: number, digits = 1): string { return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value); }
function percent(value: number): string { return `${value >= 0 ? "+" : ""}${number(value * 100, 1)}%`; }

function dateLabel(value: string): string {
  const date =
    /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? new Date(`${value}T00:00:00`)
      : new Date(value);

  return new Intl.DateTimeFormat(
    "en-US",
    {
      month: "short",
      day: "numeric",
      year: "numeric",
    },
  ).format(date);
}

function methodAssumption(
  estimatorType: string,
): string | null {
  const assumptions: Record<string, string> = {
    difference_in_differences:
      "Parallel trends should hold: without the intervention, the treated and comparison groups would have followed similar outcome trends.",

    synthetic_control:
      "The donor pool can approximate the treated unit's pre-treatment behavior well enough to provide a useful counterfactual.",

    geo_holdout:
      "Treated and holdout geographies remain comparable apart from the intervention, with limited spillover between groups.",

    marketing_mix_model:
      "Media effects can be separated from seasonality and other modeled factors given sufficient variation and historical data.",

    off_policy_evaluation:
      "Adequate support and overlap between the behavior and target policies are required for a reliable policy-value comparison.",
  };

  return assumptions[
    estimatorType
  ] ?? null;
}

export function ResultsExperience({
  state,
  onRetry,
}: {
  state: ResultsState;
  onRetry?: () => void;
}) {
  if (state.kind === "loading") return <LoadingAnalysisStatus />;
  if (state.kind === "permission") return <Message title="You don’t have access to this result" body="Ask a workspace administrator for access, or switch to the correct workspace." />;
  if (state.kind === "missing") return <Message title="We couldn’t find this analysis" body="It may have been removed or belong to another project." />;
  if (state.kind === "error") return <Message title="Results are temporarily unavailable" body="Refresh in a moment. Your completed analysis remains safely stored." />;
  const data = state.data;


  if (
    data.lifecycle_status === "succeeded"
    && data.result === null
  ) {
    const statusHref =
      `/workspaces/${data.workspace_id}`
      + `/projects/${data.project_id}`
      + `/analysis-runs/${data.analysis_run_id}`;

    return (
      <main className="results-shell">
        <section className="state-card measurement-state">
          <p className="eyebrow">
            Analysis complete
          </p>

          <h1>
            Result is being finalized
          </h1>

          <p>
            Your analysis completed, but the result is still being finalized.
          </p>

          <div className="result-state-actions">
            <a
              className="button secondary"
              href={statusHref}
            >
              Return to Status
            </a>

            {onRetry ? (
              <button
                className="button secondary"
                type="button"
                onClick={onRetry}
              >
                Retry
              </button>
            ) : null}
          </div>
        </section>
      </main>
    );
  }


  if (
    data.lifecycle_status !== "succeeded"
    || !data.result
  ) {
    return (
      <>
        {state.refreshError ? (
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
      </>
    );
  }

  const result = data.result;
  const diagnostics = result.technical_diagnostics;
  const warnings = stringArray(diagnostics.warnings);
  const decisionReady = diagnostics.causal_claim_allowed === true || diagnostics.recommendations_allowed === true;
  const conclusion = typeof diagnostics.plain_language_conclusion === "string"
    ? diagnostics.plain_language_conclusion
    : decisionReady
      ? "The analysis is ready for decision support."
      : "The estimate needs additional validation.";
  const samples = objectValue(diagnostics.sample_counts);

  const analysisStart =
    typeof data.analysis_configuration.analysis_start_date === "string"
      ? data.analysis_configuration.analysis_start_date
      : null;

  const analysisEnd =
    typeof data.analysis_configuration.analysis_end_date === "string"
      ? data.analysis_configuration.analysis_end_date
      : null;

  const analysisPeriod =
    analysisStart && analysisEnd
      ? `${dateLabel(analysisStart)} – ${dateLabel(analysisEnd)}`
      : null;

  const completedDate =
    data.completed_at
      ? dateLabel(data.completed_at)
      : null;

  const targetOutcome =
    data.target_outcome?.trim()
      || null;

  const assumption = methodAssumption(
    data.estimator_type,
  );
  const relativeLift = result.business_impact.relative_lift;
  const isMarketingMix =
    data.estimator_type === "marketing_mix_model";

  const headline =
    isMarketingMix
      ? number(result.effect_estimate)
      : relativeLift === null
        ? number(result.effect_estimate)
        : percent(relativeLift);

  const headlineLabel =
    isMarketingMix
      ? "Average media contribution"
      : data.estimator_type === "off_policy_evaluation"
        ? "Estimated policy value"
        : relativeLift === null
          ? "treatment effect"
          : "estimated lift";
  const estimatorLabel: Record<string, string> = {
    difference_in_differences: "Difference-in-differences",
    synthetic_control: "Synthetic control",
    geo_holdout: "Geo holdout",
    marketing_mix_model: "Bayesian marketing mix model",
    off_policy_evaluation: "Off-policy evaluation",
  };
  const uncertaintyCopy = data.estimator_type === "marketing_mix_model"
    ? `95% posterior interval ${number(result.confidence_interval.low)} to ${number(result.confidence_interval.high)}`
    : `95% confidence interval ${number(result.confidence_interval.low)} to ${number(result.confidence_interval.high)} · p = ${number(result.p_value, 3)}`;
  const groupMetric = data.estimator_type === "marketing_mix_model"
    ? { label: "Channels / periods", value: `${String(samples.channels ?? "—")} / ${String(samples.periods ?? "—")}` }
    : data.estimator_type === "synthetic_control"
      ? { label: "Contributing donors", value: String(Object.keys(objectValue(diagnostics.donor_weights)).length) }
      : { label: "Treated / control units", value: `${String(samples.treated_units ?? "—")} / ${String(samples.control_units ?? "—")}` };

  return (
    <main className="results-shell">
      <header className="topbar">
        <Link href="/" className="brand"><span>∆</span> Incrementality</Link>
        <div>
          <Link
            className="button secondary"
            href={`/workspaces/${data.workspace_id}/projects/${data.project_id}/analysis-runs/${data.analysis_run_id}/lineage`}
          >
            Reproducibility
          </Link>
          <Link
            className="button secondary"
            href={`/workspaces/${data.workspace_id}/projects/${data.project_id}/analysis-runs/${data.analysis_run_id}/reports`}
          >
            Reports
          </Link>
        </div>
      </header>
      <section className={`conclusion ${decisionReady ? "trusted" : "caution"}`}>
        <div>
          <p className="eyebrow">{estimatorLabel[data.estimator_type] ?? data.estimator_type} · complete</p>
          <h1>{conclusion}</h1>

          {targetOutcome || analysisPeriod || completedDate ? (
            <p className="result-header-metadata">
              {targetOutcome ? (
                <>
                  Outcome {targetOutcome}
                </>
              ) : null}

              {targetOutcome && analysisPeriod ? (
                " · "
              ) : null}

              {analysisPeriod ? (
                <>
                  Analysis period {analysisPeriod}
                </>
              ) : null}

              {(targetOutcome || analysisPeriod) && completedDate ? (
                " · "
              ) : null}

              {completedDate ? (
                <>
                  Completed {completedDate}
                </>
              ) : null}
            </p>
          ) : null}

          <p className="confidence-copy">{uncertaintyCopy}</p>
        </div>
        <div className="hero-metric"><strong>{headline}</strong><span>{headlineLabel}</span></div>
      </section>

      {!decisionReady || warnings.length ? (
        <section className="warning-panel">
          <p className="eyebrow">Diagnostic review</p><h2>Use this result with caution</h2>
          <ul>{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </section>
      ) : null}

      {assumption ? (
        <section className="panel result-assumption">
          <p className="eyebrow">
            Methodology
          </p>
          <h2>
            Method assumption
          </h2>
          <p>
            {assumption}
          </p>
        </section>
      ) : null}

      <section className="metric-grid" aria-label="Key result metrics">
        <Metric label={data.estimator_type === "marketing_mix_model" ? "Average media contribution" : "Effect per treated observation"} value={number(result.effect_estimate)} />
        <Metric label="Incremental outcome" value={result.business_impact.incremental_outcome === null ? "—" : number(result.business_impact.incremental_outcome, 0)} />
        <Metric label={groupMetric.label} value={groupMetric.value} />
        <Metric label="Observations" value={number(result.sample_size, 0)} />
      </section>

      {data.estimator_type === "synthetic_control" ? <SyntheticControlPanels diagnostics={diagnostics} /> : null}
      {data.estimator_type === "geo_holdout" ? <GeoHoldoutPanels diagnostics={diagnostics} /> : null}
      {data.estimator_type === "marketing_mix_model" ? <MarketingMixPanels diagnostics={diagnostics} /> : null}
      {data.estimator_type === "off_policy_evaluation" ? <OffPolicyEvaluationPanels diagnostics={diagnostics} /> : null}

      {data.estimator_type === "difference_in_differences" ? <><section className="story-grid">
        <article className="panel wide"><div className="panel-heading"><div><p className="eyebrow">What changed</p><h2>Observed versus expected outcome</h2></div><p>The gap after treatment is the estimated incremental impact.</p></div>{arrayValue(diagnostics.observed_vs_counterfactual).length > 0 ? (
          <ComparisonChart
            points={arrayValue(
              diagnostics.observed_vs_counterfactual,
            )}
          />
        ) : (
          <p className="result-empty-state">
            Trend-series data is not available for this historical result.
          </p>
        )}</article>
        <article className="panel"><p className="eyebrow">Business impact</p><h2>{result.business_impact.incremental_revenue === null ? "Incremental outcome" : "Estimated revenue impact"}</h2><strong className="impact-number">{result.business_impact.incremental_revenue === null ? number(result.business_impact.incremental_outcome ?? 0, 0) : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(result.business_impact.incremental_revenue)}</strong><p>Estimated across treated observations after the intervention.</p></article>
      </section>

      <section className="panel"><div className="panel-heading"><div><p className="eyebrow">Assumption check</p><h2>Effect over time</h2></div><p>Pre-treatment estimates should remain close to zero.</p></div><EventStudyChart points={arrayValue(diagnostics.event_study)} /></section></> : null}

      <details className="technical"><summary>Technical details</summary><div className="technical-grid"><Metric label="Standard error" value={number(result.standard_error, 3)} /><Metric label="Estimator" value={`${result.estimator_version} · ${result.library_name} ${result.library_version}`} /><Metric label="Model" value={String(objectValue(diagnostics.model_specification).formula ?? "Difference-in-differences")} /><Metric label="Design assessment" value={String(diagnostics.design_assessment ?? "Not available")} /></div></details>
    </main>
  );
}

function LoadingAnalysisStatus() {
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

function Metric({ label, value }: { label: string; value: string }) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div>; }
function Message({ title, body }: { title: string; body: string }) { return <main className="state-shell"><section className="state-card"><p className="eyebrow">Result unavailable</p><h1>{title}</h1><p>{body}</p></section></main>; }
