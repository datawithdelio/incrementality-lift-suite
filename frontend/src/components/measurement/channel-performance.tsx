import type { Channel, ChannelResponse, LoadState } from "@/lib/measurement/types";

import { MeasurementState } from "./results-dashboard";

const number = (value: number | null) => value === null ? "—" : new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
const label = (value: string) => { const words = value.replace("_", " "); return words[0].toUpperCase() + words.slice(1); };

export function ChannelPerformance({ state }: { state: LoadState<ChannelResponse> }) {
  if (state.kind === "loading") return <MeasurementState title="Loading channel evidence" />;
  if (state.kind === "permission") return <MeasurementState title="You don’t have access to channel performance" />;
  if (state.kind === "error") return <MeasurementState title="Channel evidence is temporarily unavailable" />;
  if (!state.data.channels.length) return <MeasurementState title="No channel-level causal evidence yet" />;
  return <><ChannelComparisonChart channels={state.data.channels} /><ChannelPerformanceTable channels={state.data.channels} /></>;
}

export function ChannelComparisonChart({ channels }: { channels: Channel[] }) {
  const maximum = Math.max(1, ...channels.map((item) => Math.max(0, item.incremental_roas ?? 0)));
  return <section className="panel channel-chart"><p className="eyebrow">Incremental return comparison</p><h2>Where causal evidence supports spend</h2><div className="channel-bars">{channels.map((item) => <div key={item.channel}><span>{item.channel}</span><i><b style={{ width: `${Math.max(0, item.incremental_roas ?? 0) / maximum * 100}%` }} /></i><strong>{number(item.incremental_roas)}</strong></div>)}</div></section>;
}

export function RecommendationBadge({ movement }: { movement: string }) {
  return <span className={`movement ${movement}`}>{label(movement)}</span>;
}

export function ChannelPerformanceTable({ channels }: { channels: Channel[] }) {
  return <section className="panel dashboard-table channel-table"><div className="table-scroll"><table><thead><tr><th>Channel</th><th>Spend</th><th>Incremental revenue</th><th>Incremental conversions</th><th>Lift</th><th>Incremental ROAS</th><th>Observed ROAS</th><th>95% interval</th><th>Contribution</th><th>Marginal response</th><th>Recommendation</th></tr></thead><tbody>{channels.map((item) => <tr key={item.channel}><td><strong>{item.channel}</strong><small>{item.reliability} reliability</small></td><td>{number(item.spend)}</td><td>{number(item.incremental_revenue)}</td><td>{number(item.incremental_conversions)}</td><td>{item.lift === null ? "—" : `${number(item.lift * 100)}%`}</td><td><strong>{number(item.incremental_roas)}</strong></td><td>{number(item.observed_roas)}</td><td>{number(item.confidence_low)}–{number(item.confidence_high)}</td><td>{number(item.contribution)}</td><td>{number(item.marginal_response)}</td><td><RecommendationBadge movement={item.recommended_movement} /><small>{item.warning}</small></td></tr>)}</tbody></table></div></section>;
}
