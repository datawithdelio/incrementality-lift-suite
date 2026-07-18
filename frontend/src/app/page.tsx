import Link from "next/link";

import { BrandMark } from "@/components/brand/brand-mark";
import { HomeGate } from "@/components/home/home-gate";

export default function Home() {
  return (
    <HomeGate>
      <main className="landing-page">
      <nav className="landing-nav" aria-label="Primary navigation">
        <Link className="landing-brand" href="/" aria-label="Incrementality home">
          <BrandMark />
        </Link>
        <div className="landing-nav-actions">
          <Link className="text-link" href="/login">Sign in</Link>
          <Link className="button button-primary" href="/register">Create workspace</Link>
        </div>
      </nav>

      <section className="landing-hero">
        <div className="landing-copy">
          <p className="landing-kicker">Evidence for every marketing decision</p>
          <h1>Measure what actually changed.</h1>
          <p className="landing-intro">Run trusted causal analyses, test their assumptions, and turn uncertainty into a decision your team can defend.</p>
          <div className="landing-actions">
            <Link className="button button-primary button-large" href="/register">Start measuring</Link>
            <Link className="button button-quiet button-large" href="/login">Open workspace</Link>
          </div>
        </div>

        <div className="evidence-visual" aria-label="Example lift result with a positive treatment effect and confidence interval">
          <div className="evidence-heading">
            <div>
              <span>Campaign lift (illustrative)</span>
              <strong>Incremental revenue</strong>
            </div>
            <span className="reliability-badge">Reliable design</span>
          </div>
          <div className="evidence-result">
            <strong>+12.4%</strong>
            <span>95% confidence interval: +7.1% to +17.8%</span>
          </div>
          <div className="evidence-chart" aria-hidden="true">
            <span className="chart-baseline" />
            <span className="chart-interval" />
            <span className="chart-estimate" />
          </div>
          <div className="evidence-footer">
            <span>Observed outcome</span>
            <span>Estimated counterfactual</span>
          </div>
        </div>
      </section>

      <section className="method-band" aria-label="Supported analysis methods">
        <p>One workflow, method-aware evidence</p>
        <div>
          <span>Difference in Differences</span>
          <span>Synthetic Control</span>
          <span>Geo Holdout</span>
          <span>Marketing Mix Modeling</span>
          <span>Off-Policy Evaluation</span>
        </div>
      </section>

      <section className="landing-principles">
        <header>
          <h2>From raw data to a decision.</h2>
          <p>Every result keeps the evidence, assumptions, and lineage close enough to inspect.</p>
        </header>
        <div className="principle-list">
          <article>
            <span>01</span>
            <div><h3>Trust before lift</h3><p>Diagnostics flag weak designs before the interface presents a causal conclusion.</p></div>
          </article>
          <article>
            <span>02</span>
            <div><h3>Reproducible by default</h3><p>Dataset, mapping, configuration, code, and library versions stay attached to every run.</p></div>
          </article>
          <article>
            <span>03</span>
            <div><h3>Built for action</h3><p>Translate uncertainty into incremental impact and clear budget guidance.</p></div>
          </article>
        </div>
      </section>
      </main>
    </HomeGate>
  );
}
