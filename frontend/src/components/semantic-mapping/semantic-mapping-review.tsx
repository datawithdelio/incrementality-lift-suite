import {
  ArrowsOutLineHorizontal,
  CalendarBlank,
  CaretDown,
  ChartLineUp,
  CheckCircle,
  Code,
  Cube,
  CurrencyDollar,
  Hash,
  Info,
  SlidersHorizontal,
} from "@phosphor-icons/react";

import type {
  CreateSemanticMappingInput,
} from "@/lib/semantic-mapping/api";

type SemanticMappingReviewProps = {
  draft: CreateSemanticMappingInput;
  includeTreatment?: boolean;
};

type MappingAssignment = {
  label: string;
  value: string;
  state?: "empty" | "treatment" | "control";
  icon: typeof CalendarBlank;
};

function mappingAssignments(
  draft: CreateSemanticMappingInput,
  includeTreatment: boolean,
): MappingAssignment[] {
  const assignments: MappingAssignment[] = [
    {
      label: "Time",
      value: draft.time_column,
      icon: CalendarBlank,
    },
    {
      label: "Unit",
      value: draft.unit_column,
      icon: Cube,
    },
    {
      label: "Outcome",
      value: draft.outcome_column,
      icon: ChartLineUp,
    },
    {
      label: "Spend",
      value:
        draft.spend_column
        ?? "Not assigned",
      state:
        draft.spend_column === null
          ? "empty"
          : undefined,
      icon: CurrencyDollar,
    },
    {
      label: "Covariates",
      value:
        draft.covariate_columns.length
        > 0
          ? draft.covariate_columns.join(
              ", ",
            )
          : "None selected",
      state:
        draft.covariate_columns.length
        === 0
          ? "empty"
          : undefined,
      icon: SlidersHorizontal,
    },
  ];

  if (includeTreatment) {
    assignments.splice(2, 0, {
      label: "Treatment",
      value: draft.treatment_column ?? "",
      icon: ArrowsOutLineHorizontal,
    });
    assignments.push(
      {
        label: "Treatment value",
        value: draft.treatment_value ?? "",
        state: "treatment",
        icon: Hash,
      },
      {
        label: "Control value",
        value: draft.control_value ?? "",
        state: "control",
        icon: Hash,
      },
    );
  }

  return assignments;
}

function reviewRequest(
  draft: CreateSemanticMappingInput,
  includeTreatment: boolean,
): Record<string, unknown> {
  if (includeTreatment) {
    return draft;
  }

  return Object.fromEntries(
    Object.entries(draft).filter(
      ([key]) =>
        ![
          "treatment_column",
          "treatment_value",
          "control_value",
        ].includes(key),
    ),
  );
}

export function SemanticMappingReview({
  draft,
  includeTreatment = true,
}: SemanticMappingReviewProps) {
  return (
    <>
      <header className="mapping-review-heading">
        <span
          className="mapping-review-heading__icon"
          aria-hidden="true"
        >
          <CheckCircle
            size={28}
            weight="duotone"
          />
        </span>

        <div>
          <h2
            id="review-save-heading"
            aria-label="Review and Save"
          >
            Review your mapping
          </h2>

          <p>
            Confirm these assignments before
            saving.
          </p>
        </div>
      </header>

      <ul
        className="mapping-assignment-list"
        aria-label="Mapping assignments"
      >
        {mappingAssignments(draft, includeTreatment).map(
          (assignment) => {
            const Icon = assignment.icon;

            return (
              <li
                key={assignment.label}
                className="mapping-assignment"
              >
                <Icon
                  size={20}
                  weight="duotone"
                  aria-hidden="true"
                />

                <span className="mapping-assignment__label">
                  {assignment.label}
                </span>

                <span
                  className={[
                    "mapping-assignment__value",
                    assignment.state
                      ? `is-${assignment.state}`
                      : "",
                  ].join(" ")}
                >
                  {assignment.value}
                </span>
              </li>
            );
          },
        )}
      </ul>

      <details className="mapping-request-details">
        <summary>
          <Code
            size={20}
            aria-hidden="true"
          />
          <span>
            View raw request JSON
          </span>
          <CaretDown
            className="mapping-request-details__caret"
            size={18}
            aria-hidden="true"
          />
        </summary>

        <pre aria-label="Semantic mapping request">
          {JSON.stringify(reviewRequest(draft, includeTreatment), null, 2)}
        </pre>
      </details>

      <p className="mapping-review-note">
        <Info
          size={18}
          weight="fill"
          aria-hidden="true"
        />
        You can edit this mapping later.
      </p>
    </>
  );
}
