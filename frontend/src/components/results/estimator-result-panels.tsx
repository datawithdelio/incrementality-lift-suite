function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}
function records(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
    : [];
}
function value(value: unknown, digits = 2): string {
  return typeof value === "number"
    ? new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value)
    : "—";
}

export function SyntheticControlPanels({ diagnostics }: { diagnostics: Record<string, unknown> }) {
  const weights = record(diagnostics.donor_weights);
  const placeboTests = records(diagnostics.placebo_tests);
  const effects = records(diagnostics.treatment_effects_over_time);
  return (
    <section className="estimator-grid">
      <article className="panel estimator-wide">
        <p className="eyebrow">Synthetic control fit</p><h2>Donor weights</h2>
        <p>The synthetic baseline is a constrained blend of the closest untreated units.</p>
        <div className="weight-list">
          {Object.entries(weights).map(([donor, weight]) => <div className="weight-row" key={donor}><span>{donor}</span><div><i style={{ width: `${Number(weight) * 100}%` }} /></div><strong>{value(Number(weight) * 100, 1)}%</strong></div>)}
        </div>
      </article>
      <article className="panel">
        <p className="eyebrow">Placebo evidence</p><h2>Is the treated gap unusual?</h2>
        <strong className="impact-number">p = {value(diagnostics.placebo_p_value, 3)}</strong>
        <p>{placeboTests.length} untreated units were tested as if they had received treatment.</p>
      </article>
      <article className="panel estimator-full">
        <div className="panel-heading"><div><p className="eyebrow">Treatment effect</p><h2>Incremental effect over time</h2></div><p>Post-treatment gaps between observed and synthetic outcomes.</p></div>
        <div className="effect-strip">{effects.map((item, index) => <div key={String(item.period ?? index)}><i style={{ height: `${Math.min(100, Math.max(5, Math.abs(Number(item.effect ?? 0)) * 8))}%` }} /><span>{String(item.period ?? index)}</span><strong>{value(item.effect)}</strong></div>)}</div>
      </article>
    </section>
  );
}

export function GeoHoldoutPanels({ diagnostics }: { diagnostics: Record<string, unknown> }) {
  const assignments = records(diagnostics.geographic_assignments);
  const balance = record(diagnostics.balance_diagnostics);
  return (
    <section className="estimator-grid">
      <article className="panel estimator-wide">
        <p className="eyebrow">Geographic lift</p><h2>Treatment and holdout map</h2>
        <div className="geo-map" role="img" aria-label="Geographic treatment and holdout assignments">
          {assignments.map((item, index) => {
            const latitude = Number(item.latitude ?? 0); const longitude = Number(item.longitude ?? 0);
            return <span key={String(item.geo ?? index)} className={`geo-dot ${item.assignment === "treatment" ? "treated" : "holdout"}`} style={{ left: `${((longitude + 180) / 360) * 100}%`, top: `${((90 - latitude) / 180) * 100}%` }} title={`${String(item.geo)} · ${String(item.assignment)}`} />;
          })}
        </div>
        <div className="map-key"><span className="treated">Treatment</span><span>Holdout</span></div>
      </article>
      <article className="panel">
        <p className="eyebrow">Balance diagnostics</p><h2>Pre-period comparability</h2>
        <strong className="impact-number">{value(balance.standardized_mean_difference)}</strong>
        <p>Standardized mean difference before campaign exposure. Values closer to zero indicate stronger balance.</p>
      </article>
    </section>
  );
}

export function MarketingMixPanels({ diagnostics }: { diagnostics: Record<string, unknown> }) {
  const contributions = record(diagnostics.channel_contributions);
  const roas = record(diagnostics.channel_roas);
  const scenarios = records(diagnostics.scenario_plan);
  const maxContribution = Math.max(1, ...Object.values(contributions).map(Number));
  return (
    <section className="estimator-grid">
      <article className="panel estimator-wide">
        <p className="eyebrow">Posterior media decomposition</p><h2>Channel contribution</h2>
        <div className="contribution-list">{Object.entries(contributions).map(([channel, contribution]) => <div key={channel}><div><strong>{channel}</strong><span>ROAS {value(roas[channel])}</span></div><i style={{ width: `${(Number(contribution) / maxContribution) * 100}%` }} /><b>{value(contribution, 0)}</b></div>)}</div>
      </article>
      <article className="panel">
        <p className="eyebrow">Budget scenario</p><h2>Recommended next move</h2>
        {scenarios.length ? scenarios.map((scenario, index) => <div className="scenario" key={index}><strong>{String(scenario.recommended_channel)}</strong><p>{String(scenario.scenario)}</p><span>{value(scenario.budget_to_reallocate, 0)} available to reallocate</span></div>) : <p>Recommendations are withheld until convergence and data checks pass.</p>}
      </article>
      <article className="panel estimator-full">
        <p className="eyebrow">Model health</p><h2>Bayesian convergence</h2>
        <div className="technical-grid"><MiniMetric label="Maximum R-hat" value={value(record(diagnostics.convergence).max_r_hat, 3)} /><MiniMetric label="Minimum effective samples" value={value(record(diagnostics.convergence).min_effective_sample_size, 0)} /><MiniMetric label="Divergences" value={value(record(diagnostics.convergence).divergences, 0)} /></div>
      </article>
    </section>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div>; }
