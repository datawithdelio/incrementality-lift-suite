import {
  GeoResultMap,
  type GeoResultAssignment,
} from "@/components/results/geo-result-map";

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}
function records(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> =>
        Boolean(item && typeof item === "object"),
      )
    : [];
}
function value(value: unknown, digits = 2): string {
  return typeof value === "number"
    ? new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(
        value,
      )
    : "—";
}

function pValueText(input: unknown): string {
  const numeric = Number(input);

  if (!Number.isFinite(numeric)) {
    return "p unavailable";
  }

  if (numeric < 0.001) {
    return "p < 0.001";
  }

  return `p = ${new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 3,
  }).format(numeric)}`;
}

export function SyntheticControlPanels({
  diagnostics,
}: {
  diagnostics: Record<string, unknown>;
}) {
  const weights = record(diagnostics.donor_weights);
  const placeboTests = records(diagnostics.placebo_tests);
  const effects = records(diagnostics.treatment_effects_over_time);
  return (
    <section className="estimator-grid">
      <article className="panel estimator-wide">
        <p className="eyebrow">Synthetic control fit</p>
        <h2>Donor weights</h2>
        <p>
          The synthetic baseline is a constrained blend of the closest untreated
          units.
        </p>
        <div className="weight-list">
          {Object.entries(weights).map(([donor, weight]) => (
            <div className="weight-row" key={donor}>
              <span>{donor}</span>
              <div>
                <i style={{ width: `${Number(weight) * 100}%` }} />
              </div>
              <strong>{value(Number(weight) * 100, 1)}%</strong>
            </div>
          ))}
        </div>
      </article>
      <article className="panel">
        <p className="eyebrow">Placebo evidence</p>
        <h2>Is the treated gap unusual?</h2>
        <strong className="impact-number">
          {pValueText(diagnostics.placebo_p_value)}
        </strong>
        <p>
          {placeboTests.length} untreated units were tested as if they had
          received treatment.
        </p>
      </article>
      <article className="panel estimator-full">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Treatment effect</p>
            <h2>Incremental effect over time</h2>
          </div>
          <p>Post-treatment gaps between observed and synthetic outcomes.</p>
        </div>
        <div className="effect-strip">
          {effects.map((item, index) => (
            <div key={String(item.period ?? index)}>
              <i
                style={{
                  height: `${Math.min(100, Math.max(5, Math.abs(Number(item.effect ?? 0)) * 8))}%`,
                }}
              />
              <span>{String(item.period ?? index)}</span>
              <strong>{value(item.effect)}</strong>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

export function GeoHoldoutPanels({
  diagnostics,
  effectEstimate,
  relativeLift,
  sampleSize,
}: {
  diagnostics: Record<string, unknown>;
  effectEstimate: number;
  relativeLift: number | null;
  sampleSize: number;
}) {
  const balance = record(diagnostics.balance_diagnostics);

  const assignments: GeoResultAssignment[] = records(
    diagnostics.geographic_assignments,
  ).flatMap((item) => {
    const geo = String(item.geo ?? "").trim();

    const latitude = Number(item.latitude);

    const longitude = Number(item.longitude);

    const assignment =
      item.assignment === "treatment"
        ? "treatment"
        : item.assignment === "holdout"
          ? "holdout"
          : null;

    if (
      !geo ||
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      assignment === null
    ) {
      return [];
    }

    return [
      {
        geo,
        latitude,
        longitude,
        assignment,
      },
    ];
  });

  const standardizedMeanDifference = Number(
    balance.standardized_mean_difference,
  );

  const prePeriodBalance = Number.isFinite(standardizedMeanDifference)
    ? standardizedMeanDifference
    : null;

  const boundedBalance =
    prePeriodBalance === null ? 0 : Math.max(-1, Math.min(1, prePeriodBalance));

  const balancePosition = ((boundedBalance + 1) / 2) * 100;

  const gaugeAngle = Math.PI - (balancePosition / 100) * Math.PI;

  const gaugeX = 110 + 90 * Math.cos(gaugeAngle);

  const gaugeY = 100 - 90 * Math.sin(gaugeAngle);

  return (
    <section className="estimator-grid geo-holdout-grid">
      <article className="panel estimator-wide geo-map-card">
        <div className="geo-panel-heading">
          <div>
            <p className="eyebrow">Geographic lift</p>

            <h2>Treatment and holdout map</h2>
          </div>

          <span className="geo-assignment-count">
            {assignments.length} geographies
          </span>
        </div>

        <GeoResultMap
          assignments={assignments}
          effectEstimate={effectEstimate}
          relativeLift={relativeLift}
          sampleSize={sampleSize}
          prePeriodBalance={prePeriodBalance}
        />

        <div className="map-key">
          <span className="treated">
            <i aria-hidden="true" />
            Treatment
          </span>

          <span className="holdout">
            <i aria-hidden="true" />
            Holdout
          </span>
        </div>
      </article>

      <article className="panel geo-balance-card">
        <div>
          <p className="eyebrow">Balance diagnostics</p>

          <h2>Pre-period comparability</h2>
        </div>

        <strong className="impact-number">
          {value(balance.standardized_mean_difference)}
        </strong>

        <p className="geo-balance-description">
          Standardized mean difference before campaign exposure. Values closer
          to zero indicate stronger balance.
        </p>

        <div
          className="balance-gauge"
          aria-label={`Pre-period standardized mean difference ${value(
            balance.standardized_mean_difference,
          )}`}
        >
          <svg viewBox="0 0 220 116" role="img" aria-hidden="true">
            <path
              className="balance-gauge-track"
              d="M20 100 A90 90 0 0 1 200 100"
              pathLength="100"
            />

            <path
              className="balance-gauge-progress"
              d="M20 100 A90 90 0 0 1 200 100"
              pathLength="100"
              strokeDasharray={`${balancePosition} 100`}
            />

            <line
              className="balance-gauge-zero"
              x1="110"
              y1="5"
              x2="110"
              y2="18"
            />

            <circle
              className="balance-gauge-marker"
              cx={gaugeX}
              cy={gaugeY}
              r="7"
            />
          </svg>

          <div className="balance-gauge-scale">
            <span>-1</span>
            <span>0</span>
            <span>1</span>
          </div>

          <strong className="balance-gauge-value">
            {value(balance.standardized_mean_difference)}
          </strong>
        </div>
      </article>
    </section>
  );
}

export function MarketingMixPanels({
  diagnostics,
}: {
  diagnostics: Record<string, unknown>;
}) {
  const contributions = record(diagnostics.channel_contributions);
  const roas = record(diagnostics.channel_roas);
  const scenarios = records(diagnostics.scenario_plan);
  const maxContribution = Math.max(
    1,
    ...Object.values(contributions).map(Number),
  );
  return (
    <section className="estimator-grid">
      <article className="panel estimator-wide">
        <p className="eyebrow">Posterior media decomposition</p>
        <h2>Channel contribution</h2>
        <div className="contribution-list">
          {Object.entries(contributions).map(([channel, contribution]) => (
            <div key={channel}>
              <div>
                <strong>{channel}</strong>
                <span>ROAS {value(roas[channel])}</span>
              </div>
              <i
                style={{
                  width: `${(Number(contribution) / maxContribution) * 100}%`,
                }}
              />
              <b>{value(contribution, 0)}</b>
            </div>
          ))}
        </div>
      </article>
      <article className="panel">
        <p className="eyebrow">Budget scenario</p>
        <h2>Recommended next move</h2>
        {scenarios.length ? (
          scenarios.map((scenario, index) => (
            <div className="scenario" key={index}>
              <strong>{String(scenario.recommended_channel)}</strong>
              <p>{String(scenario.scenario)}</p>
              <span>
                {value(scenario.budget_to_reallocate, 0)} available to
                reallocate
              </span>
            </div>
          ))
        ) : (
          <p>
            Recommendations are withheld until convergence and data checks pass.
          </p>
        )}
      </article>
      <article className="panel estimator-full">
        <p className="eyebrow">Model health</p>
        <h2>Bayesian convergence</h2>
        <div className="technical-grid">
          <MiniMetric
            label="Maximum R-hat"
            value={value(record(diagnostics.convergence).max_r_hat, 3)}
          />
          <MiniMetric
            label="Minimum effective samples"
            value={value(
              record(diagnostics.convergence).min_effective_sample_size,
              0,
            )}
          />
          <MiniMetric
            label="Divergences"
            value={value(record(diagnostics.convergence).divergences, 0)}
          />
        </div>
      </article>
    </section>
  );
}

export function OffPolicyEvaluationPanels({
  diagnostics,
}: {
  diagnostics: Record<string, unknown>;
}) {
  const estimates = record(diagnostics.policy_estimates);
  const overlap = record(diagnostics.propensity_overlap);
  return (
    <section className="estimator-grid">
      <article className="panel estimator-wide">
        <p className="eyebrow">Policy comparison</p>
        <h2>{String(diagnostics.policy_name ?? "Candidate policy")}</h2>
        <div className="policy-comparison">
          {Object.entries(estimates).map(([method, estimate]) => (
            <div key={method}>
              <span>{method.replaceAll("_", " ")}</span>
              <strong>{value(estimate, 3)}</strong>
            </div>
          ))}
        </div>
      </article>
      <article className="panel">
        <p className="eyebrow">Reliability evidence</p>
        <h2>Effective sample size</h2>
        <strong className="impact-number">
          {value(diagnostics.effective_sample_size, 0)}
        </strong>
        <p>
          {String(
            diagnostics.plain_language_warning ??
              "Overlap evidence is unavailable.",
          )}
        </p>
      </article>
      <article className="panel estimator-full">
        <p className="eyebrow">Propensity overlap</p>
        <h2>Weight stability</h2>
        <div className="technical-grid">
          <MiniMetric
            label="Maximum importance weight"
            value={value(overlap.maximum_importance_weight, 2)}
          />
          <MiniMetric
            label="Extreme weights"
            value={value(diagnostics.extreme_weight_count, 0)}
          />
        </div>
      </article>
    </section>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
