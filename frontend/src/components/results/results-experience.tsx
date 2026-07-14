"use client";

import type { AnalysisResultResponse, ResultsState } from "@/lib/results/types";
import Link from "next/link";

import { ComparisonChart, EventStudyChart } from "./result-charts";
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

function downloadReport(data: AnalysisResultResponse) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `analysis-${data.analysis_run_id}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

export function ResultsExperience({ state }: { state: ResultsState }) {
  if (state.kind === "loading") return <StatusState status="running" />;
  if (state.kind === "permission") return <Message title="You don’t have access to this result" body="Ask a workspace administrator for access, or switch to the correct workspace." />;
  if (state.kind === "missing") return <Message title="We couldn’t find this analysis" body="It may have been removed or belong to another project." />;
  if (state.kind === "error") return <Message title="Results are temporarily unavailable" body="Refresh in a moment. Your completed analysis remains safely stored." />;
  const data = state.data;
  if (data.lifecycle_status !== "succeeded" || !data.result) {
    return <StatusState status={data.lifecycle_status} attempt={data.attempt_count ? `Attempt ${data.attempt_count} of ${data.max_attempts}` : undefined} />;
  }

  const result = data.result;
  const diagnostics = result.technical_diagnostics;
  const warnings = stringArray(diagnostics.warnings);
  const causal = diagnostics.causal_claim_allowed === true;
  const conclusion = typeof diagnostics.plain_language_conclusion === "string"
    ? diagnostics.plain_language_conclusion
    : causal ? "The design supports a measurable incremental effect." : "The estimate needs additional validation.";
  const samples = objectValue(diagnostics.sample_counts);
  const relativeLift = result.business_impact.relative_lift;
  const headline = relativeLift === null ? number(result.effect_estimate) : percent(relativeLift);

  return (
    <main className="results-shell">
      <header className="topbar">
        <Link href="/" className="brand"><span>∆</span> Incrementality</Link>
        <button className="button secondary" onClick={() => downloadReport(data)}>Download report</button>
      </header>
      <section className={`conclusion ${causal ? "trusted" : "caution"}`}>
        <div>
          <p className="eyebrow">Difference-in-differences · complete</p>
          <h1>{conclusion}</h1>
          <p className="confidence-copy">95% confidence interval {number(result.confidence_interval.low)} to {number(result.confidence_interval.high)} · p = {number(result.p_value, 3)}</p>
        </div>
        <div className="hero-metric"><strong>{headline}</strong><span>{relativeLift === null ? "treatment effect" : "estimated lift"}</span></div>
      </section>

      {!causal || warnings.length ? (
        <section className="warning-panel">
          <p className="eyebrow">Diagnostic review</p><h2>Use this result with caution</h2>
          <ul>{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </section>
      ) : null}

      <section className="metric-grid" aria-label="Key result metrics">
        <Metric label="Effect per treated observation" value={number(result.effect_estimate)} />
        <Metric label="Incremental outcome" value={result.business_impact.incremental_outcome === null ? "—" : number(result.business_impact.incremental_outcome, 0)} />
        <Metric label="Treated / control units" value={`${String(samples.treated_units ?? "—")} / ${String(samples.control_units ?? "—")}`} />
        <Metric label="Observations" value={number(result.sample_size, 0)} />
      </section>

      <section className="story-grid">
        <article className="panel wide"><div className="panel-heading"><div><p className="eyebrow">What changed</p><h2>Observed versus expected outcome</h2></div><p>The gap after treatment is the estimated incremental impact.</p></div><ComparisonChart points={arrayValue(diagnostics.observed_vs_counterfactual)} /></article>
        <article className="panel"><p className="eyebrow">Business impact</p><h2>{result.business_impact.incremental_revenue === null ? "Incremental outcome" : "Estimated revenue impact"}</h2><strong className="impact-number">{result.business_impact.incremental_revenue === null ? number(result.business_impact.incremental_outcome ?? 0, 0) : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(result.business_impact.incremental_revenue)}</strong><p>Estimated across treated observations after the intervention.</p></article>
      </section>

      <section className="panel"><div className="panel-heading"><div><p className="eyebrow">Assumption check</p><h2>Effect over time</h2></div><p>Pre-treatment estimates should remain close to zero.</p></div><EventStudyChart points={arrayValue(diagnostics.event_study)} /></section>

      <details className="technical"><summary>Technical details</summary><div className="technical-grid"><Metric label="Standard error" value={number(result.standard_error, 3)} /><Metric label="Estimator" value={`${result.estimator_version} · ${result.library_name} ${result.library_version}`} /><Metric label="Model" value={String(objectValue(diagnostics.model_specification).formula ?? "Difference-in-differences")} /><Metric label="Design assessment" value={String(diagnostics.design_assessment ?? "Not available")} /></div><pre>{JSON.stringify({ analysis_configuration: data.analysis_configuration, diagnostics }, null, 2)}</pre></details>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div>; }
function Message({ title, body }: { title: string; body: string }) { return <main className="state-shell"><section className="state-card"><p className="eyebrow">Result unavailable</p><h1>{title}</h1><p>{body}</p></section></main>; }
