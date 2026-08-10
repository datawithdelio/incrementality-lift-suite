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


type MarketingMixFitPoint = {
  period: string;
  observed: number;
  fittedMean: number;
  fittedLow: number;
  fittedHigh: number;
  residual: number;
};

type MarketingMixIntervalPoint = {
  channel: string;
  mean: number;
  low: number;
  high: number;
};

const MMM_CHART_WIDTH = 760;
const MMM_CHART_HEIGHT = 240;
const MMM_CHART_LEFT = 44;
const MMM_CHART_RIGHT = 18;
const MMM_CHART_TOP = 18;
const MMM_CHART_BOTTOM = 30;

function finiteDiagnosticNumber(input: unknown): number | null {
  return typeof input === "number" && Number.isFinite(input)
    ? input
    : null;
}

function marketingMixFitPoints(input: unknown): MarketingMixFitPoint[] {
  return records(input).flatMap((item) => {
    const period = typeof item.period === "string" ? item.period : null;
    const observed = finiteDiagnosticNumber(item.observed);
    const fittedMean = finiteDiagnosticNumber(item.fitted_mean);
    const fittedLow = finiteDiagnosticNumber(item.fitted_low);
    const fittedHigh = finiteDiagnosticNumber(item.fitted_high);
    const residual = finiteDiagnosticNumber(item.residual);

    if (
      period === null
      || observed === null
      || fittedMean === null
      || fittedLow === null
      || fittedHigh === null
      || residual === null
    ) {
      return [];
    }

    return [
      {
        period,
        observed,
        fittedMean,
        fittedLow,
        fittedHigh,
        residual,
      },
    ];
  });
}

function marketingMixIntervalPoints(
  contributions: Record<string, unknown>,
  input: unknown,
): MarketingMixIntervalPoint[] {
  const intervals = record(input);

  return Object.entries(contributions).flatMap(([channel, rawMean]) => {
    const mean = finiteDiagnosticNumber(rawMean);
    const interval = record(intervals[channel]);
    const low = finiteDiagnosticNumber(interval.low);
    const high = finiteDiagnosticNumber(interval.high);

    if (mean === null || low === null || high === null) {
      return [];
    }

    return [
      {
        channel,
        mean,
        low: Math.min(low, high),
        high: Math.max(low, high),
      },
    ];
  });
}

function chartExtent(
  values: number[],
  includeZero = false,
): [number, number] {
  const candidates = includeZero ? [...values, 0] : values;

  if (!candidates.length) {
    return [0, 1];
  }

  let minimum = Math.min(...candidates);
  let maximum = Math.max(...candidates);

  if (!Number.isFinite(minimum) || !Number.isFinite(maximum)) {
    return [0, 1];
  }

  if (minimum === maximum) {
    const padding = Math.max(Math.abs(minimum) * 0.1, 1);
    return [minimum - padding, maximum + padding];
  }

  const padding = (maximum - minimum) * 0.08;
  minimum -= padding;
  maximum += padding;

  return [minimum, maximum];
}

function chartX(index: number, count: number): number {
  const usableWidth = MMM_CHART_WIDTH - MMM_CHART_LEFT - MMM_CHART_RIGHT;

  if (count <= 1) {
    return MMM_CHART_LEFT + usableWidth / 2;
  }

  return MMM_CHART_LEFT + (index / (count - 1)) * usableWidth;
}

function chartY(
  input: number,
  minimum: number,
  maximum: number,
): number {
  const usableHeight =
    MMM_CHART_HEIGHT - MMM_CHART_TOP - MMM_CHART_BOTTOM;

  return (
    MMM_CHART_TOP
    + ((maximum - input) / (maximum - minimum)) * usableHeight
  );
}

function periodLabel(period: string): string {
  const parsed = new Date(period);

  if (Number.isNaN(parsed.getTime())) {
    return period;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

function ObservedVsFittedChart({
  points,
}: {
  points: MarketingMixFitPoint[];
}) {
  const [minimum, maximum] = chartExtent(
    points.flatMap((point) => [
      point.observed,
      point.fittedLow,
      point.fittedHigh,
    ]),
  );

  const observedPoints = points
    .map(
      (point, index) =>
        `${chartX(index, points.length)},${chartY(
          point.observed,
          minimum,
          maximum,
        )}`,
    )
    .join(" ");

  const fittedPoints = points
    .map(
      (point, index) =>
        `${chartX(index, points.length)},${chartY(
          point.fittedMean,
          minimum,
          maximum,
        )}`,
    )
    .join(" ");

  const upperBand = points.map(
    (point, index) =>
      `${chartX(index, points.length)},${chartY(
        point.fittedHigh,
        minimum,
        maximum,
      )}`,
  );

  const lowerBand = [...points]
    .reverse()
    .map((point, reverseIndex) => {
      const index = points.length - reverseIndex - 1;

      return `${chartX(index, points.length)},${chartY(
        point.fittedLow,
        minimum,
        maximum,
      )}`;
    });

  return (
    <article className="panel estimator-full mmm-diagnostic-chart">
      <p className="eyebrow">Model fit</p>
      <h2>Observed vs fitted outcome</h2>
      <p className="mmm-chart-description">
        Observed outcome compared with the saved posterior fitted mean and
        its 95% interval.
      </p>

      <div className="mmm-chart-frame">
        <svg
          viewBox={`0 0 ${MMM_CHART_WIDTH} ${MMM_CHART_HEIGHT}`}
          role="img"
          aria-label="Observed versus fitted outcome over time"
          className="mmm-time-chart"
        >
          <line
            className="mmm-chart-axis"
            x1={MMM_CHART_LEFT}
            y1={MMM_CHART_HEIGHT - MMM_CHART_BOTTOM}
            x2={MMM_CHART_WIDTH - MMM_CHART_RIGHT}
            y2={MMM_CHART_HEIGHT - MMM_CHART_BOTTOM}
          />

          <polygon
            className="mmm-fit-band"
            points={[...upperBand, ...lowerBand].join(" ")}
          />

          <polyline
            className="mmm-fitted-line"
            points={fittedPoints}
          />

          <polyline
            className="mmm-observed-line"
            points={observedPoints}
          />
        </svg>
      </div>

      <div className="mmm-chart-legend" aria-hidden="true">
        <span>
          <i className="mmm-legend-observed" />
          Observed
        </span>
        <span>
          <i className="mmm-legend-fitted" />
          Fitted mean
        </span>
        <span>
          <i className="mmm-legend-band" />
          95% posterior interval
        </span>
      </div>

      <div className="mmm-chart-axis-labels">
        <span>{periodLabel(points[0].period)}</span>
        <span>{periodLabel(points[points.length - 1].period)}</span>
      </div>
    </article>
  );
}

function ChannelContributionUncertaintyChart({
  points,
}: {
  points: MarketingMixIntervalPoint[];
}) {
  const width = MMM_CHART_WIDTH;
  const labelWidth = 175;
  const rightPadding = 26;
  const rowHeight = 42;
  const topPadding = 26;
  const height = Math.max(
    150,
    topPadding * 2 + points.length * rowHeight,
  );

  const [minimum, maximum] = chartExtent(
    points.flatMap((point) => [
      point.low,
      point.mean,
      point.high,
    ]),
    true,
  );

  const x = (input: number) =>
    labelWidth
    + ((input - minimum) / (maximum - minimum))
      * (width - labelWidth - rightPadding);

  return (
    <article className="panel estimator-full mmm-diagnostic-chart">
      <p className="eyebrow">Posterior uncertainty</p>
      <h2>Channel contribution uncertainty</h2>
      <p className="mmm-chart-description">
        Saved 95% posterior intervals for total modeled contribution by
        channel.
      </p>

      <div className="mmm-chart-frame">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label="Channel contribution posterior intervals"
          className="mmm-interval-chart"
        >
          {minimum < 0 && maximum > 0 ? (
            <line
              className="mmm-zero-line"
              x1={x(0)}
              y1={12}
              x2={x(0)}
              y2={height - 12}
            />
          ) : null}

          {points.map((point, index) => {
            const y = topPadding + index * rowHeight + rowHeight / 2;

            return (
              <g key={point.channel}>
                <text
                  className="mmm-channel-label"
                  x={8}
                  y={y + 4}
                >
                  {point.channel}
                </text>

                <line
                  className="mmm-interval-line"
                  x1={x(point.low)}
                  y1={y}
                  x2={x(point.high)}
                  y2={y}
                />

                <line
                  className="mmm-interval-cap"
                  x1={x(point.low)}
                  y1={y - 6}
                  x2={x(point.low)}
                  y2={y + 6}
                />

                <line
                  className="mmm-interval-cap"
                  x1={x(point.high)}
                  y1={y - 6}
                  x2={x(point.high)}
                  y2={y + 6}
                />

                <circle
                  className="mmm-interval-point"
                  cx={x(point.mean)}
                  cy={y}
                  r={5}
                />
              </g>
            );
          })}
        </svg>
      </div>

      <p className="mmm-chart-note">
        Wider intervals indicate greater uncertainty in the channel-level
        contribution estimate.
      </p>
    </article>
  );
}

function ResidualsChart({
  points,
}: {
  points: MarketingMixFitPoint[];
}) {
  const [minimum, maximum] = chartExtent(
    points.map((point) => point.residual),
    true,
  );

  const residualPoints = points
    .map(
      (point, index) =>
        `${chartX(index, points.length)},${chartY(
          point.residual,
          minimum,
          maximum,
        )}`,
    )
    .join(" ");

  const zeroY = chartY(0, minimum, maximum);

  return (
    <article className="panel estimator-full mmm-diagnostic-chart">
      <p className="eyebrow">Model diagnostics</p>
      <h2>Residuals over time</h2>
      <p className="mmm-chart-description">
        Observed outcome minus the saved posterior fitted mean for each
        modeled period.
      </p>

      <div className="mmm-chart-frame">
        <svg
          viewBox={`0 0 ${MMM_CHART_WIDTH} ${MMM_CHART_HEIGHT}`}
          role="img"
          aria-label="Model residuals over time"
          className="mmm-time-chart"
        >
          <line
            className="mmm-zero-line"
            x1={MMM_CHART_LEFT}
            y1={zeroY}
            x2={MMM_CHART_WIDTH - MMM_CHART_RIGHT}
            y2={zeroY}
          />

          <polyline
            className="mmm-residual-line"
            points={residualPoints}
          />
        </svg>
      </div>

      <div className="mmm-chart-axis-labels">
        <span>{periodLabel(points[0].period)}</span>
        <span>{periodLabel(points[points.length - 1].period)}</span>
      </div>

      <p className="mmm-chart-note">
        Residuals that fluctuate around zero without a persistent pattern
        indicate a better systematic fit.
      </p>
    </article>
  );
}

export function MarketingMixPanels({
  diagnostics,
}: {
  diagnostics: Record<string, unknown>;
}) {
  const contributions = record(diagnostics.channel_contributions);
  const efficiency = record(diagnostics.channel_efficiency);
  const legacyRoas = record(diagnostics.channel_roas);
  const efficiencyValues =
    Object.keys(efficiency).length > 0
      ? efficiency
      : legacyRoas;
  const efficiencyMetric =
    typeof diagnostics.channel_efficiency_metric === "string"
      ? diagnostics.channel_efficiency_metric
      : Object.keys(legacyRoas).length > 0
        ? "incremental_revenue_per_dollar"
        : null;
  const efficiencyLabel =
    efficiencyMetric === "incremental_conversions_per_dollar"
      ? "Conversions / $"
      : efficiencyMetric === "incremental_outcome_units_per_dollar"
        ? "Outcome units / $"
        : "ROAS";

  const efficiencyDigits =
    efficiencyMetric === "incremental_conversions_per_dollar"
    || efficiencyMetric === "incremental_outcome_units_per_dollar"
      ? 4
      : 2;
  const scenarios = records(diagnostics.scenario_plan);
  const modelFitPoints = marketingMixFitPoints(
    diagnostics.model_fit_series,
  );
  const intervalPoints = marketingMixIntervalPoints(
    contributions,
    diagnostics.posterior_intervals,
  );
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
                <span>
                  {efficiencyLabel} {value(efficiencyValues[channel], efficiencyDigits)}
                </span>
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

      {modelFitPoints.length ? (
        <ObservedVsFittedChart points={modelFitPoints} />
      ) : null}

      {intervalPoints.length ? (
        <ChannelContributionUncertaintyChart points={intervalPoints} />
      ) : null}

      {modelFitPoints.length ? (
        <ResidualsChart points={modelFitPoints} />
      ) : null}
    </section>
  );
}

export function OffPolicyEvaluationPanels({
  diagnostics,
  probabilityScale = false,
}: {
  diagnostics: Record<string, unknown>;
  probabilityScale?: boolean;
}) {
  const estimates = record(diagnostics.policy_estimates);
  const overlap = record(diagnostics.propensity_overlap);
  return (
    <section className="estimator-grid">
      <article className="panel estimator-wide">
        <p className="eyebrow">Estimator comparison</p>
        <h2>{String(diagnostics.policy_name ?? "Candidate policy")}</h2>
        <div className="policy-comparison">
          {Object.entries(estimates).map(([method, estimate]) => {
            const numericEstimate = Number(estimate);
            const renderedEstimate =
              probabilityScale && Number.isFinite(numericEstimate)
                ? `${value(numericEstimate * 100, 1)}%`
                : value(estimate, 3);

            return (
              <div key={method}>
                <span>{method.replaceAll("_", " ")}</span>
                <strong>{renderedEstimate}</strong>
              </div>
            );
          })}
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
