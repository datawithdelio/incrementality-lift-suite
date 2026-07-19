"use client";

import {
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  SESSION_TOKEN_KEY,
} from "@/lib/auth/api";

import {
  humanizeAnalysisRunQueueError,
  queueAnalysisRun,
} from "@/lib/analysis-configuration/api";

import {
  mapAnalysisConfigurationRequest,
  type AnalysisConfigurationDraft,
  type FilterOperator,
} from "@/lib/analysis-configuration/request";

import {
  analysisRunPath,
} from "@/lib/projects/routes";

type MappingTreatment = {
  column: string | null;
  treatmentValue: string | null;
  controlValue: string | null;
};

type Props = {
  draft: AnalysisConfigurationDraft;
  mappingTreatment: MappingTreatment;

  workspaceId: string;
  projectId: string;

  datasetId: string;
  semanticMappingVersion: number;
};

const ESTIMATOR_LABELS = {
  difference_in_differences:
    "Difference in Differences",

  synthetic_control:
    "Synthetic Control",

  geo_holdout:
    "Geo Holdout",

  marketing_mix_model:
    "Marketing Mix Modeling",

  off_policy_evaluation:
    "Off-policy Evaluation",
} satisfies Record<
  AnalysisConfigurationDraft[
    "estimatorType"
  ],
  string
>;

const OPERATOR_LABELS = {
  equals: "Equals",
  not_equals: "Not equals",
  contains: "Contains",

  greater_than:
    "Greater than",

  greater_than_or_equal:
    "Greater than or equal",

  less_than:
    "Less than",

  less_than_or_equal:
    "Less than or equal",

  is_null:
    "Is null",

  is_not_null:
    "Is not null",
} satisfies Record<
  FilterOperator,
  string
>;

export function AnalysisConfigurationReview({
  draft,
  mappingTreatment,
  workspaceId,
  projectId,
  datasetId,
  semanticMappingVersion,
}: Props) {
  const router =
    useRouter();

  const [
    isSubmitting,
    setIsSubmitting,
  ] = useState(false);

  const [
    submissionError,
    setSubmissionError,
  ] = useState<
    string | null
  >(null);

  async function handleQueueAnalysis():
    Promise<void> {
    if (isSubmitting) {
      return;
    }

    const token =
      window.localStorage.getItem(
        SESSION_TOKEN_KEY,
      );

    if (!token) {
      setSubmissionError(
        "Your session has expired. "
        + "Sign in again and retry.",
      );

      return;
    }

    setIsSubmitting(true);
    setSubmissionError(null);

    try {
      const request =
        mapAnalysisConfigurationRequest(
          draft,
          {
            datasetId,
            semanticMappingVersion,
          },
        );

      const run =
        await queueAnalysisRun(
          token,
          workspaceId,
          projectId,
          request,
        );

      router.push(
        analysisRunPath(
          workspaceId,
          projectId,
          run.id,
        ),
      );

      // Intentionally leave the action disabled.
      // Navigation is now in progress and a second
      // analysis run must not be queued.
    } catch (error) {
      setSubmissionError(
        humanizeAnalysisRunQueueError(
          error,
        ),
      );

      setIsSubmitting(false);
    }
  }

  return (
    <main>
      <h1>
        Configure Analysis
      </h1>

      <section
        aria-labelledby={
          "review-analysis-heading"
        }
      >
        <h2
          id={
            "review-analysis-heading"
          }
        >
          Review analysis configuration
        </h2>

        <section>
          <h3>Method</h3>

          <p>
            {
              ESTIMATOR_LABELS[
                draft.estimatorType
              ]
            }
          </p>
        </section>

        <section>
          <h3>
            Analysis period
          </h3>

          <p>
            {
              draft.period
                .analysisStartDate
            }
            {" → "}
            {
              draft.period
                .analysisEndDate
            }
          </p>

          {draft.period
            .interventionDate !== null
            && (
              <p>
                Intervention:{" "}
                {
                  draft.period
                    .interventionDate
                }
              </p>
            )}
        </section>

        {draft.treatmentControl.kind
          === "mapped_binary"
          && (
            <section>
              <h3>
                Treatment and control
              </h3>

              <p>
                Treatment column:{" "}
                {
                  mappingTreatment
                    .column
                }
              </p>

              <p>
                Treatment value:{" "}
                {
                  mappingTreatment
                    .treatmentValue
                }
              </p>

              <p>
                Control value:{" "}
                {
                  mappingTreatment
                    .controlValue
                }
              </p>
            </section>
          )}

        {draft.treatmentControl.kind
          === "synthetic_control"
          && (
            <section>
              <h3>
                Treatment and control
              </h3>

              <p>
                Treated unit:{" "}
                {
                  draft
                    .treatmentControl
                    .treatedUnit
                }
              </p>

              <p>
                Donor pool:{" "}
                {draft
                  .treatmentControl
                  .donorPool
                  .join(", ")}
              </p>
            </section>
          )}

        {draft.treatmentControl.kind
          === "geo_holdout"
          && (
            <section>
              <h3>
                Treatment and control
              </h3>

              <p>
                Treated geographies:{" "}
                {draft
                  .treatmentControl
                  .treatedGeographies
                  .join(", ")}
              </p>

              <p>
                Control geographies:{" "}
                {draft
                  .treatmentControl
                  .controlGeographies
                  .join(", ")}
              </p>
            </section>
          )}

        {draft.treatmentControl.kind
          === "off_policy_evaluation"
          && (
            <section>
              <h3>
                Policy assignment
              </h3>

              <p>
                Policy:{" "}
                {
                  draft
                    .treatmentControl
                    .policyName
                }
              </p>

              <p>
                Behavior propensity
                column:{" "}
                {
                  draft
                    .treatmentControl
                    .behaviorPropensityColumn
                }
              </p>

              <p>
                Target propensity
                column:{" "}
                {
                  draft
                    .treatmentControl
                    .targetPropensityColumn
                }
              </p>
            </section>
          )}

        <section>
          <h3>
            Population filters
          </h3>

          {draft.selection
            .rowFilters
            .length === 0
            ? (
              <p>
                No filters applied.
              </p>
            )
            : (
              draft.selection
                .rowFilters
                .map(
                  (
                    rule,
                    index,
                  ) => (
                    <p
                      key={[
                        rule.column,
                        rule.operator,
                        index,
                      ].join("-")}
                    >
                      {rule.column}
                      {" · "}
                      {
                        OPERATOR_LABELS[
                          rule.operator
                        ]
                      }

                      {rule.value
                        === undefined
                        ? ""
                        : ` · ${String(
                            rule
                              .value
                              .value,
                          )}`}
                    </p>
                  ),
                )
            )}
        </section>

        {submissionError
          !== null
          && (
            <p
              role="alert"
              aria-live="assertive"
            >
              {submissionError}
            </p>
          )}

        <button
          type="button"
          disabled={
            isSubmitting
          }
          onClick={() => {
            void handleQueueAnalysis();
          }}
        >
          {isSubmitting
            ? "Queueing analysis…"
            : "Queue analysis"}
        </button>
      </section>
    </main>
  );
}
