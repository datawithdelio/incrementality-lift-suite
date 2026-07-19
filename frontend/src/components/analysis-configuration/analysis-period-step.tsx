type AnalysisPeriodStepProps = {
  analysisStartDate: string;
  interventionDate: string;
  analysisEndDate: string;

  showInterventionDate: boolean;

  validationError:
    string | null;

  previewError:
    string | null;

  previewLoading: boolean;
  canContinue: boolean;

  onAnalysisStartDateChange: (
    value: string,
  ) => void;

  onInterventionDateChange: (
    value: string,
  ) => void;

  onAnalysisEndDateChange: (
    value: string,
  ) => void;

  onContinue: () => void;
};

export function AnalysisPeriodStep({
  analysisStartDate,
  interventionDate,
  analysisEndDate,
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
  return (
    <main>
      <h1>
        Configure Analysis
      </h1>

      <section
        aria-labelledby="analysis-period-heading"
      >
        <h2 id="analysis-period-heading">
          Define analysis period
        </h2>

        <p>
          Set the date range the backend
          should use for this analysis.
        </p>

        <label>
          <span>
            Analysis start date
          </span>

          <input
            type="date"
            aria-label="Analysis start date"
            value={analysisStartDate}
            onChange={(event) => {
              onAnalysisStartDateChange(
                event.target.value,
              );
            }}
          />
        </label>

        {showInterventionDate && (
          <label>
            <span>
              Intervention date
            </span>

            <input
              type="date"
              aria-label="Intervention date"
              value={interventionDate}
              onChange={(event) => {
                onInterventionDateChange(
                  event.target.value,
                );
              }}
            />
          </label>
        )}

        <label>
          <span>
            Analysis end date
          </span>

          <input
            type="date"
            aria-label="Analysis end date"
            value={analysisEndDate}
            onChange={(event) => {
              onAnalysisEndDateChange(
                event.target.value,
              );
            }}
          />
        </label>

        {validationError !== null && (
          <p role="alert">
            {validationError}
          </p>
        )}

        {previewError !== null && (
          <p role="alert">
            {previewError}
          </p>
        )}

        <button
          type="button"
          disabled={
            !canContinue
            || previewLoading
          }
          onClick={onContinue}
        >
          {previewLoading
            ? "Loading…"
            : "Continue"}
        </button>
      </section>
    </main>
  );
}
