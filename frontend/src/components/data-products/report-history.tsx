"use client";

import {
  useRef,
  useState,
} from "react";

import {
  downloadReport,
} from "@/lib/data-products/api";
import type {
  ReportJob,
} from "@/lib/data-products/types";

type ReportHistoryProps = {
  reports: ReportJob[];
  workspaceId: string;
  projectId: string;
  runId: string;
  onRegenerate?: (
    format: string,
  ) => void;
  regenerateDisabled?: boolean;
};

function reportStatusLabel(
  report: ReportJob,
): string {
  if (
    report.status === "pending"
    && report.attempt_count > 0
  ) {
    return "Retrying";
  }

  return (
    report.status.charAt(0).toUpperCase()
    + report.status.slice(1)
  );
}

export function ReportHistory({
  reports,
  workspaceId,
  projectId,
  runId,
  onRegenerate,
  regenerateDisabled = false,
}: ReportHistoryProps) {
  const downloadInFlight = useRef(false);

  const [
    downloadingReportId,
    setDownloadingReportId,
  ] = useState<string | null>(null);

  const [
    downloadErrorReportId,
    setDownloadErrorReportId,
  ] = useState<string | null>(null);

  async function startDownload(
    report: ReportJob,
  ): Promise<void> {
    if (downloadInFlight.current) {
      return;
    }

    const token = localStorage.getItem(
      "incrementality_session_token",
    );

    if (!token) {
      setDownloadErrorReportId(
        report.id,
      );
      return;
    }

    downloadInFlight.current = true;
    setDownloadingReportId(
      report.id,
    );
    setDownloadErrorReportId(null);

    let objectUrl: string | null = null;

    try {
      const {
        blob,
        filename,
      } = await downloadReport(
        workspaceId,
        projectId,
        runId,
        report.id,
        token,
      );

      objectUrl =
        URL.createObjectURL(blob);

      const anchor =
        document.createElement("a");

      anchor.href = objectUrl;
      anchor.download = filename;

      document.body.appendChild(
        anchor,
      );

      anchor.click();
      anchor.remove();
    } catch {
      setDownloadErrorReportId(
        report.id,
      );
    } finally {
      if (objectUrl !== null) {
        URL.revokeObjectURL(
          objectUrl,
        );
      }

      downloadInFlight.current =
        false;

      setDownloadingReportId(
        null,
      );
    }
  }

  if (reports.length === 0) {
    return (
      <section
        className="state-card measurement-state"
      >
        <h1>
          No reports generated yet
        </h1>
      </section>
    );
  }

  return (
    <section
      className="panel report-history"
    >
      <p className="eyebrow">
        Report history
      </p>

      <h2>
        Reproducible exports
      </h2>

      <div>
        {reports.map(
          (report) => (
            <article
              key={report.id}
            >
              <div>
                <strong>
                  {
                    report.format
                      .toUpperCase()
                  }
                  {" · version "}
                  {report.version}
                </strong>

                <span>
                  {
                    new Date(
                      report.created_at,
                    ).toLocaleDateString()
                  }
                </span>
              </div>

              <span
                className={
                  `status-pill ${report.status}`
                }
              >
                {
                  reportStatusLabel(
                    report,
                  )
                }
              </span>

              {report.status
              === "succeeded" ? (
                <>
                  <button
                    className="button secondary"
                    disabled={
                      downloadingReportId
                      !== null
                    }
                    onClick={() =>
                      void startDownload(
                        report,
                      )
                    }
                  >
                    {
                      downloadingReportId
                      === report.id
                        ? "Downloading…"
                        : downloadErrorReportId
                            === report.id
                          ? "Try Download Again"
                          : "Download"
                    }
                  </button>

                  {downloadErrorReportId
                  === report.id ? (
                    <small
                      role="alert"
                    >
                      Download failed.
                      {" "}
                      Please try again.
                    </small>
                  ) : null}
                </>
              ) : (
                <>
                  <small>
                    {
                      report.failure_reason
                      ?? (
                        `Attempt ${report.attempt_count}`
                        + ` of ${report.max_attempts}`
                      )
                    }
                  </small>

                  {
                    report.status
                      === "failed"
                    && onRegenerate
                      ? (
                        <button
                          className="button secondary"
                          disabled={
                            regenerateDisabled
                          }
                          onClick={() =>
                            onRegenerate(
                              report.format,
                            )
                          }
                        >
                          Regenerate{" "}
                          {
                            report.format
                              .toUpperCase()
                          }
                        </button>
                      )
                      : null
                  }
                </>
              )}
            </article>
          ),
        )}
      </div>
    </section>
  );
}
