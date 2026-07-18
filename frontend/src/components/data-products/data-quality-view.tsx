import type {
  DataQuality,
  LoadState,
  QualityFinding,
} from "../../lib/data-products/types";

type DataQualityViewProps =
  | {
      quality: DataQuality;
      state?: never;
    }
  | {
      state: LoadState<DataQuality>;
      quality?: never;
    };

function severityLabel(severity: string): string {
  if (!severity) {
    return "Info";
  }

  return severity.charAt(0).toUpperCase() + severity.slice(1);
}

function summaryLabel(
  count: number,
  singular: string,
  plural: string = `${singular}s`,
): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function QualityFindingItem({
  finding,
}: {
  finding: QualityFinding;
}) {
  return (
    <article>
      <p>{severityLabel(finding.severity)}</p>
      <h3>{finding.rule_id}</h3>

      {finding.recommendation ? (
        <p>{finding.recommendation}</p>
      ) : null}
    </article>
  );
}

function DataQualityContent({
  quality,
}: {
  quality: DataQuality;
}) {
  const activeFindings = quality.findings.filter(
    (finding) => !finding.passed,
  );
  const passedChecks = quality.findings.filter(
    (finding) => finding.passed,
  );

  const blockingCount = activeFindings.filter(
    (finding) => finding.severity === "blocking",
  ).length;
  const warningCount = activeFindings.filter(
    (finding) => finding.severity === "warning",
  ).length;
  const infoCount = activeFindings.filter(
    (finding) => finding.severity === "info",
  ).length;

  const hasBlockingIssues = !quality.ready;
  const hasWarnings = warningCount > 0;

  const readinessLabel = hasBlockingIssues
    ? "Needs attention"
    : hasWarnings
      ? "Dataset ready with warnings"
      : "Dataset ready";

  return (
    <>
      <p>{readinessLabel}</p>

      <div aria-label="Validation summary">
        <p>
          {summaryLabel(
            blockingCount,
            "blocking issue",
          )}
        </p>
        <p>{summaryLabel(warningCount, "warning")}</p>
        <p>{summaryLabel(infoCount, "info", "info")}</p>
        <p>
          {summaryLabel(
            passedChecks.length,
            "passed check",
          )}
        </p>
      </div>

      {hasBlockingIssues ? (
        <p role="alert">
          This dataset cannot be used for analysis until the blocking issues are corrected.
        </p>
      ) : hasWarnings ? (
        <p>
          You may continue, but review these issues before running an analysis.
        </p>
      ) : null}

      {activeFindings.length === 0 ? (
        <p role="status">
          No data-quality issues were found.
        </p>
      ) : (
        <div>
          {activeFindings.map((finding) => (
            <QualityFindingItem
              key={finding.rule_id}
              finding={finding}
            />
          ))}
        </div>
      )}

      {passedChecks.length > 0 ? (
        <section aria-labelledby="passed-checks-heading">
          <h2 id="passed-checks-heading">
            Passed checks
          </h2>

          {passedChecks.map((finding) => (
            <QualityFindingItem
              key={finding.rule_id}
              finding={finding}
            />
          ))}
        </section>
      ) : null}
    </>
  );
}

export function DataQualityView(
  props: DataQualityViewProps,
) {
  if ("state" in props && props.state) {
    if (props.state.kind === "loading") {
      return (
        <section aria-labelledby="data-quality-heading">
          <h1 id="data-quality-heading">Data Quality</h1>
          <p role="status">Loading validation summary</p>
        </section>
      );
    }

    if (props.state.kind === "error") {
      return (
        <section aria-labelledby="data-quality-heading">
          <h1 id="data-quality-heading">Data Quality</h1>
          <p role="alert">
            We couldn&apos;t load the data-quality results.
          </p>
        </section>
      );
    }

    if (props.state.kind === "permission") {
      return (
        <section aria-labelledby="data-quality-heading">
          <h1 id="data-quality-heading">Data Quality</h1>
          <p role="alert">
            You don’t have access to this dataset.
          </p>
        </section>
      );
    }

    return (
      <section aria-labelledby="data-quality-heading">
        <h1 id="data-quality-heading">Data Quality</h1>
        <DataQualityContent quality={props.state.data} />
      </section>
    );
  }

  return (
    <section aria-labelledby="data-quality-heading">
      <h1 id="data-quality-heading">Data Quality</h1>
      <DataQualityContent quality={props.quality} />
    </section>
  );
}
