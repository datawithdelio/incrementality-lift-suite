import type { LifecycleStatus } from "@/lib/results/types";

const copy: Record<LifecycleStatus, { eyebrow: string; title: string; body: string }> = {
  queued: {
    eyebrow: "Queued",
    title: "Analysis queued",
    body: "We’ll start as soon as processing capacity is available. This page updates automatically.",
  },
  running: {
    eyebrow: "Running",
    title: "Analysis running",
    body: "Your analysis is currently being processed.",
  },
  retrying: {
    eyebrow: "Retrying",
    title: "Retrying analysis",
    body: "A temporary service issue interrupted the first attempt. No action is needed from you.",
  },
  failed: {
    eyebrow: "Needs attention",
    title: "This analysis needs attention",
    body: "Check the data and analysis design, then create a new run. Your source data was not changed.",
  },
  cancelled: {
    eyebrow: "Cancelled",
    title: "Analysis cancelled",
    body: "Start a new run whenever you’re ready.",
  },
  succeeded: { eyebrow: "Complete", title: "Analysis complete", body: "" },
};

export function StatusState({ status, attempt }: { status: LifecycleStatus; attempt?: string }) {
  const content = copy[status];
  return (
    <main className="state-shell">
      <section className="state-card" aria-live="polite">
        <div className={`status-orbit status-${status}`} aria-hidden="true"><span /></div>
        <p className="eyebrow">{content.eyebrow}</p>
        <h1>{content.title}</h1>
        <p>{content.body}</p>

        {status === "running" ? (
          <div
            role="progressbar"
            aria-label="Analysis running"
            className="analysis-running-progress"
          />
        ) : null}

        {attempt ? <p className="attempt">{attempt}</p> : null}
      </section>
    </main>
  );
}
