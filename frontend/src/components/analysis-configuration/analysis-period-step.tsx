type AnalysisPeriodStepProps = {
  analysisStartDate: string;
  interventionDate: string;
  analysisEndDate: string;
  datasetMinimumDate?: string | null;
  datasetMaximumDate?: string | null;
  showInterventionDate: boolean;
  validationError: string | null;
  previewError: string | null;
  previewLoading: boolean;
  canContinue: boolean;
  onAnalysisStartDateChange: (value: string) => void;
  onInterventionDateChange: (value: string) => void;
  onAnalysisEndDateChange: (value: string) => void;
  onContinue: () => void;
};

type PeriodFieldProps = {
  label: string;
  description: string;
  value: string;
  badge: string;
  badgeTone: "pre" | "intervention" | "post";
  minimumDate: string | null;
  maximumDate: string | null;
  onChange: (value: string) => void;
};

function PeriodField({
  label,
  description,
  value,
  badge,
  badgeTone,
  minimumDate,
  maximumDate,
  onChange,
}: PeriodFieldProps) {
  return (
    <label className="analysis-period-field">
      <span className="analysis-period-field__copy">
        <strong>{label}</strong>
        <small>{description}</small>
      </span>

      <input
        type="date"
        aria-label={label}
        value={value}
        min={minimumDate ?? undefined}
        max={maximumDate ?? undefined}
        onChange={(event) => {
          onChange(event.target.value);
        }}
      />

      <span className="analysis-period-field__badge" data-tone={badgeTone}>
        <span aria-hidden="true" />
        {badge}
      </span>
    </label>
  );
}

function displayDate(value: string): string {
  if (!value) {
    return "Select date";
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function AnalysisPeriodStep({
  analysisStartDate,
  interventionDate,
  analysisEndDate,
  datasetMinimumDate = null,
  datasetMaximumDate = null,
  showInterventionDate,
  validationError,
  previewError,
  previewLoading,
  canContinue,
  onAnalysisStartDateChange,
  onInterventionDateChange,
  onAnalysisEndDateChange,
  onContinue,
}: AnalysisPeriodStepProps) {
  const activeError = validationError ?? previewError;

  return (
    <main className="analysis-period-shell">
      <header className="analysis-period-hero">
        <p className="analysis-period-hero__eyebrow">Analysis setup</p>

        <h1>Configure Analysis</h1>

        <p>
          Define the period used to measure baseline performance and incremental
          impact.
        </p>
      </header>

      <section
        className="analysis-period-card"
        aria-labelledby="analysis-period-heading"
      >
        <header className="analysis-period-card__header">
          <span className="analysis-period-card__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M7 3v3M17 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </span>

          <span>
            <h2 id="analysis-period-heading">Define analysis period</h2>

            <p>Set the date range the backend should use for this analysis.</p>
          </span>
        </header>

        <div
          className="analysis-period-fields"
          data-columns={showInterventionDate ? "three" : "two"}
        >
          <PeriodField
            label="Analysis start date"
            description="Beginning of the pre-period."
            value={analysisStartDate}
            badge="Pre-period"
            badgeTone="pre"
            minimumDate={datasetMinimumDate}
            maximumDate={datasetMaximumDate}
            onChange={onAnalysisStartDateChange}
          />

          {showInterventionDate && (
            <PeriodField
              label="Intervention date"
              description="When the change or test began."
              value={interventionDate}
              badge="Intervention"
              badgeTone="intervention"
              minimumDate={datasetMinimumDate}
              maximumDate={datasetMaximumDate}
              onChange={onInterventionDateChange}
            />
          )}

          <PeriodField
            label="Analysis end date"
            description="End of the post-period."
            value={analysisEndDate}
            badge={showInterventionDate ? "Post-period" : "Analysis end"}
            badgeTone="post"
            minimumDate={datasetMinimumDate}
            maximumDate={datasetMaximumDate}
            onChange={onAnalysisEndDateChange}
          />
        </div>

        <div className="analysis-period-guidance" role="note">
          <span aria-hidden="true">i</span>

          <p>
            <strong>
              {showInterventionDate
                ? "The intervention must fall between the start and end dates."
                : "Choose a complete continuous analysis window."}
            </strong>

            <small>
              {showInterventionDate
                ? "This ensures the analysis includes usable pre- and post-intervention periods."
                : "The selected range will be used for the complete time-series analysis."}
            </small>
          </p>
        </div>

        <div
          className="analysis-period-timeline"
          aria-label="Analysis period timeline"
        >
          <div className="analysis-period-timeline__track">
            <span />
            {showInterventionDate && <span />}
            <span />
          </div>

          <div
            className="analysis-period-timeline__labels"
            data-columns={showInterventionDate ? "three" : "two"}
          >
            <span>
              <strong>{displayDate(analysisStartDate)}</strong>
              <small>Start of pre-period</small>
            </span>

            {showInterventionDate && (
              <span>
                <strong>{displayDate(interventionDate)}</strong>
                <small>Intervention</small>
              </span>
            )}

            <span>
              <strong>{displayDate(analysisEndDate)}</strong>
              <small>End of analysis</small>
            </span>
          </div>
        </div>

        {activeError !== null && (
          <p className="analysis-period-error" role="alert">
            {activeError}
          </p>
        )}

        <footer className="analysis-period-actions">
          <span>
            {canContinue
              ? "Dates are ready for the next step."
              : "Complete the required dates to continue."}
          </span>

          <button
            type="button"
            disabled={!canContinue || previewLoading}
            onClick={onContinue}
          >
            {previewLoading ? "Loading…" : "Continue"}

            {!previewLoading && <span aria-hidden="true">→</span>}
          </button>
        </footer>
      </section>
    </main>
  );
}
