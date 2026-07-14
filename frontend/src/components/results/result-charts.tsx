type Point = Record<string, unknown>;

function numeric(value: unknown): number { return typeof value === "number" ? value : 0; }

export function ComparisonChart({ points }: { points: Point[] }) {
  const ceiling = Math.max(1, ...points.flatMap((p) => [numeric(p.observed), numeric(p.counterfactual)]));
  return (
    <div className="chart" role="img" aria-label="Observed outcome compared with estimated counterfactual">
      <div className="chart-legend"><span className="observed-key">Observed</span><span className="counter-key">Counterfactual</span></div>
      <div className="bar-chart">
        {points.map((point, index) => (
          <div className="bar-group" key={String(point.period ?? index)}>
            <div className="bars">
              <span className="bar observed" style={{ height: `${(numeric(point.observed) / ceiling) * 100}%` }} />
              <span className="bar counter" style={{ height: `${(numeric(point.counterfactual) / ceiling) * 100}%` }} />
            </div>
            <small>{String(point.period ?? index)}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

export function EventStudyChart({ points }: { points: Point[] }) {
  const max = Math.max(1, ...points.map((point) => Math.abs(numeric(point.coefficient))));
  return (
    <div className="event-chart" role="img" aria-label="Event-study coefficients before and after treatment">
      <div className="zero-line" />
      {points.map((point, index) => {
        const value = numeric(point.coefficient);
        return (
          <div className="event-point" key={String(point.period ?? index)}>
            <span className={`event-stem ${value < 0 ? "negative" : ""}`} style={{ height: `${Math.max(2, Math.abs(value / max) * 42)}%` }} />
            <span className="event-dot" />
            <small>{String(point.period ?? index)}</small>
          </div>
        );
      })}
    </div>
  );
}
