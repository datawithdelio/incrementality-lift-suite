import type { DataQuality, DatasetPreview, LoadState } from "@/lib/data-products/types";
import type { Dataset } from "@/lib/datasets/api";

const number = (value: number) => new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);

function formatPreviewValue(value: unknown): string {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }

  return String(value);
}

function formatDatasetStatus(status: string): string {
  return status
    .replaceAll("_", " ")
    .replace(/^./, (character) =>
      character.toUpperCase(),
    );
}

function formatByteSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const kilobytes = bytes / 1024;

  if (kilobytes < 1024) {
    return `${new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 1,
    }).format(kilobytes)} KB`;
  }

  return `${new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
  }).format(kilobytes / 1024)} MB`;
}

export function DataExplorer({
  state,
  quality,
  dataset,
}: {
  state: LoadState<DatasetPreview>;
  quality?: DataQuality;
  dataset?: Dataset;
}) {
  if (state.kind === "loading") return <State title="Profiling your dataset" />;
  if (state.kind === "permission") return <State title="You don’t have access to this dataset" />;
  if (state.kind === "error") return <State title="This dataset could not be inspected" />;
  const data = state.data;
  if (!data.total_rows) return <State title="This dataset has no rows" />;
  const names = Object.keys(data.rows[0] ?? {});
  return <>
    {dataset ? (
      <section
        className="explorer-summary"
        aria-label="Dataset metadata"
      >
        <article>
          <span>Dataset</span>
          <strong>{dataset.source_filename}</strong>
        </article>

        <article>
          <span>Status</span>
          <strong>
            {formatDatasetStatus(dataset.status)}
          </strong>
        </article>

        <article>
          <span>Rows</span>
          <strong>
            {dataset.row_count === null
              ? "—"
              : number(dataset.row_count)}
          </strong>
        </article>

        <article>
          <span>Columns</span>
          <strong>
            {dataset.column_count === null
              ? "—"
              : number(dataset.column_count)}
          </strong>
        </article>

        <article>
          <span>File size</span>
          <strong>{formatByteSize(dataset.byte_size)}</strong>
        </article>

        <article>
          <span>Uploaded</span>
          <strong>
            {dataset.uploaded_at
              ? new Date(dataset.uploaded_at).toLocaleString()
              : "Not uploaded yet"}
          </strong>
        </article>
      </section>
    ) : null}

    <section className="explorer-summary"><article><span>Dataset size</span><strong>{number(data.total_rows)} rows</strong></article><article><span>Current view</span><strong>Page {number(data.page)} of {number(data.total_pages)}</strong></article><article><span>Date range</span><strong>{data.date_range ? `${data.date_range.minimum} – ${data.date_range.maximum}` : "Not detected"}</strong></article><article><span>Quality score</span><strong>{quality ? `${quality.score}/100` : "Assessing"}</strong></article></section>
    <section className="panel profile-strip"><p className="eyebrow">Column profiles</p><div>{data.columns.map((column) => <article key={column.name}><strong>{column.name}</strong><span>{column.inferred_type}</span><small>{number(column.missing_percentage)}% missing · {number(column.unique_count)} unique</small><small>Min {String(column.minimum ?? "—")} · Max {String(column.maximum ?? "—")}</small>{column.mean !== null ? <small>Mean {number(column.mean)} · Median {number(column.median ?? 0)}</small> : null}</article>)}</div></section>
    <DistributionPanels data={data} />
    <section className="panel explorer-table"><div className="table-scroll"><table><thead><tr>{names.map((name) => <th key={name}>{name}</th>)}</tr></thead><tbody>{data.rows.map((row, index) => <tr key={index}>{names.map((name) => <td key={name}>{formatPreviewValue(row[name])}</td>)}</tr>)}</tbody></table></div></section>
    {quality ? <QualityPanel quality={quality} /> : null}
  </>;
}

function DistributionPanels({ data }: { data: DatasetPreview }) {
  const treatment = Object.entries(data.treatment_distribution);
  const maximum = Math.max(1, ...treatment.map(([, count]) => count));
  return <section className="distribution-grid"><article className="panel"><p className="eyebrow">Treatment and control</p><h2>Group distribution</h2><div className="distribution-bars">{treatment.map(([group, count]) => <div key={group}><span>{group}</span><i><b style={{ width: `${count / maximum * 100}%` }} /></i><strong>{number(count)}</strong></div>)}</div></article><article className="panel"><p className="eyebrow">Outcome distribution</p><h2>Range and center</h2><div className="technical-grid">{Object.entries(data.outcome_distribution).map(([metric, value]) => <div className="metric" key={metric}><span>{metric}</span><strong>{number(value)}</strong></div>)}</div></article></section>;
}

function QualityPanel({ quality }: { quality: DataQuality }) {
  return <section className="panel quality-panel"><div className="panel-heading"><div><p className="eyebrow">Method readiness</p><h2>{quality.ready ? "Ready to analyze" : "Fix blocking issues first"}</h2></div><strong>{quality.score}/100</strong></div><div className="finding-list">{quality.findings.map((item) => <article className={item.severity} key={item.rule_id}><span>{item.passed ? "Passed" : item.severity}</span><strong>{item.rule_id.replaceAll("_", " ")}</strong><p>{item.recommendation}</p></article>)}</div></section>;
}

function State({ title }: { title: string }) {
  return <section className="state-card measurement-state"><p className="eyebrow">Data Explorer</p><h1>{title}</h1></section>;
}
