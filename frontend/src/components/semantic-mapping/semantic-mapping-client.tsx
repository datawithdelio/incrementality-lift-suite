"use client";

import Link from "next/link";
import {
  useEffect,
  useState,
} from "react";

import { SESSION_TOKEN_KEY } from "@/lib/auth/api";
import {
  datasetExplorePath,
  datasetQualityPath,
} from "@/lib/datasets/routes";
import { fetchPreview } from "@/lib/data-products/api";
import type {
  ColumnSummary,
} from "@/lib/data-products/types";
import {
  getDataset,
  type Dataset,
} from "@/lib/datasets/api";
import {
  createSemanticMapping,
  getLatestSemanticMapping,
  type CreateSemanticMappingInput,
  type SemanticMapping,
} from "@/lib/semantic-mapping/api";

type SemanticMappingClientProps = {
  workspaceId: string;
  projectId: string;
  datasetId: string;
};

type WizardStep = 1 | 2 | 3 | 4 | 5 | 6;

const SEMANTIC_MAPPING_STEPS = [
  {
    number: 1,
    label: "Time",
  },
  {
    number: 2,
    label: "Unit",
  },
  {
    number: 3,
    label: "Treatment",
  },
  {
    number: 4,
    label: "Outcome",
  },
  {
    number: 5,
    label: "Spend and Covariates",
  },
  {
    number: 6,
    label: "Review and Save",
  },
] as const;

type SaveState =
  | { kind: "idle" }
  | { kind: "saving" }
  | {
      kind: "success";
      version: number;
    }
  | {
      kind: "error";
      message: string;
    };

type SemanticMappingState =
  | { kind: "loading" }
  | {
      kind: "blocked";
      dataset: Dataset;
    }
  | {
      kind: "ready";
      dataset: Dataset;
      columns: ColumnSummary[];
      rows: Array<Record<string, unknown>>;
      mapping: SemanticMapping | null;
      draft: CreateSemanticMappingInput;
    }
  | {
      kind: "error";
      message: string;
    };

function emptyDraft(): CreateSemanticMappingInput {
  return {
    time_column: "",
    unit_column: "",
    treatment_column: "",
    outcome_column: "",
    spend_column: null,
    covariate_columns: [],
    treatment_value: "",
    control_value: "",
  };
}

function draftFromMapping(
  mapping: SemanticMapping | null,
): CreateSemanticMappingInput {
  if (mapping === null) {
    return emptyDraft();
  }

  return {
    time_column: mapping.time_column,
    unit_column: mapping.unit_column,
    treatment_column: mapping.treatment_column,
    outcome_column: mapping.outcome_column,
    spend_column: mapping.spend_column,
    covariate_columns: [
      ...mapping.covariate_columns,
    ],
    treatment_value: mapping.treatment_value,
    control_value: mapping.control_value,
  };
}

function isValidTimeColumn(
  column: ColumnSummary,
): boolean {
  return (
    column.inferred_type === "date"
    || column.inferred_type === "datetime"
  );
}

function isValidUnitColumn(
  column: ColumnSummary,
): boolean {
  return (
    column.inferred_type === "string"
    || column.inferred_type === "integer"
  );
}

function isValidTreatmentColumn(
  column: ColumnSummary,
): boolean {
  return (
    column.inferred_type === "boolean"
    || column.inferred_type === "integer"
    || column.inferred_type === "string"
  );
}

type SemanticRole =
  | "time_column"
  | "unit_column"
  | "treatment_column"
  | "outcome_column"
  | "spend_column"
  | "covariate_columns";

function isColumnAssignedElsewhere(
  draft: CreateSemanticMappingInput,
  columnName: string,
  currentRole: SemanticRole,
): boolean {
  const scalarRoles = [
    ["time_column", draft.time_column],
    ["unit_column", draft.unit_column],
    ["treatment_column", draft.treatment_column],
    ["outcome_column", draft.outcome_column],
    ["spend_column", draft.spend_column],
  ] as const;

  const assignedToAnotherScalarRole =
    scalarRoles.some(
      ([role, value]) =>
        role !== currentRole
        && value !== null
        && value !== ""
        && value === columnName,
    );

  const assignedAsCovariate =
    currentRole !== "covariate_columns"
    && draft.covariate_columns.includes(
      columnName,
    );

  return (
    assignedToAnotherScalarRole
    || assignedAsCovariate
  );
}

function isValidOutcomeColumn(
  column: ColumnSummary,
): boolean {
  return (
    column.inferred_type === "integer"
    || column.inferred_type === "float"
  );
}

type SemanticMappingValidationColumn = {
  name: string;
  inferred_type: string;
};

function validateSemanticMappingDraft(
  draft: CreateSemanticMappingInput,
  columns: readonly SemanticMappingValidationColumn[],
): string | null {
  const columnsByName = new Map(
    columns.map((column) => [
      column.name,
      column,
    ]),
  );

  const timeColumn = columnsByName.get(
    draft.time_column,
  );

  if (
    !timeColumn
    || !["date", "datetime"].includes(
      timeColumn.inferred_type,
    )
  ) {
    return "Choose a valid time column before continuing.";
  }

  const unitColumn = columnsByName.get(
    draft.unit_column,
  );

  if (
    !unitColumn
    || !["string", "integer"].includes(
      unitColumn.inferred_type,
    )
  ) {
    return "Choose a valid unit column before continuing.";
  }

  const treatmentColumn = columnsByName.get(
    draft.treatment_column,
  );

  if (
    !treatmentColumn
    || ![
      "boolean",
      "integer",
      "string",
    ].includes(
      treatmentColumn.inferred_type,
    )
  ) {
    return "Choose a valid treatment column before continuing.";
  }

  const outcomeColumn = columnsByName.get(
    draft.outcome_column,
  );

  if (
    !outcomeColumn
    || !["integer", "float"].includes(
      outcomeColumn.inferred_type,
    )
  ) {
    return "Choose a valid outcome column before continuing.";
  }

  if (draft.spend_column !== null) {
    const spendColumn = columnsByName.get(
      draft.spend_column,
    );

    if (
      !spendColumn
      || !["integer", "float"].includes(
        spendColumn.inferred_type,
      )
    ) {
      return "Spend column must be numeric.";
    }
  }

  const assignedRoles = [
    draft.time_column,
    draft.unit_column,
    draft.treatment_column,
    draft.outcome_column,
    ...(draft.spend_column === null
      ? []
      : [draft.spend_column]),
  ];

  if (
    assignedRoles.some(
      (columnName) =>
        columnName.length > 255,
    )
    || draft.covariate_columns.some(
      (columnName) =>
        columnName.length > 255,
    )
  ) {
    return "Mapped column name must not exceed 255 characters.";
  }

  if (
    new Set(assignedRoles).size
    !== assignedRoles.length
  ) {
    return "Semantic roles must use distinct columns.";
  }

  if (
    new Set(
      draft.covariate_columns,
    ).size
    !== draft.covariate_columns.length
  ) {
    return "Covariate columns must be unique.";
  }

  for (
    const columnName
    of draft.covariate_columns
  ) {
    if (!columnsByName.has(columnName)) {
      return `Mapped column '${columnName}' does not exist.`;
    }
  }

  if (
    draft.covariate_columns.some(
      (columnName) =>
        assignedRoles.includes(
          columnName,
        ),
    )
  ) {
    return "Covariate columns must not overlap assigned semantic roles.";
  }

  const treatmentValue =
    draft.treatment_value.trim();

  const controlValue =
    draft.control_value.trim();

  if (!treatmentValue) {
    return "Treatment value must not be blank.";
  }

  if (!controlValue) {
    return "Control value must not be blank.";
  }

  if (treatmentValue.length > 255) {
    return "Treatment value must not exceed 255 characters.";
  }

  if (controlValue.length > 255) {
    return "Control value must not exceed 255 characters.";
  }

  if (
    treatmentValue.toLocaleLowerCase()
    === controlValue.toLocaleLowerCase()
  ) {
    return "Treatment and control values must be distinct.";
  }

  return null;
}

function observedColumnValues(
  rows: Array<Record<string, unknown>>,
  columnName: string,
): string[] {
  if (!columnName) {
    return [];
  }

  const values: string[] = [];
  const seen = new Set<string>();

  for (const row of rows) {
    const rawValue = row[columnName];

    if (
      rawValue === null
      || rawValue === undefined
    ) {
      continue;
    }

    const value = String(rawValue).trim();

    if (
      value.length === 0
      || seen.has(value)
    ) {
      continue;
    }

    seen.add(value);
    values.push(value);
  }

  return values;
}

export function SemanticMappingClient({
  workspaceId,
  projectId,
  datasetId,
}: SemanticMappingClientProps) {
  const [state, setState] =
    useState<SemanticMappingState>({
      kind: "loading",
    });
  const [stepError, setStepError] =
    useState<string | null>(null);
  const [step, setStep] =
    useState<WizardStep>(1);
  const [saveState, setSaveState] =
    useState<SaveState>({
      kind: "idle",
    });

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const token = window.localStorage.getItem(
      SESSION_TOKEN_KEY,
    );

    if (!token) {
      queueMicrotask(() => {
        if (active) {
          setState({
            kind: "error",
            message:
              "Your session is no longer available. Please sign in again.",
          });
        }
      });

      return () => {
        active = false;
        controller.abort();
      };
    }

    async function load(sessionToken: string): Promise<void> {
      try {
        const dataset = await getDataset(
          sessionToken,
          workspaceId,
          projectId,
          datasetId,
        );

        if (!active) {
          return;
        }

        if (dataset.status !== "ready") {
          setState({
            kind: "blocked",
            dataset,
          });
          return;
        }

        const [
          preview,
          mapping,
        ] = await Promise.all([
          fetchPreview(
            workspaceId,
            projectId,
            datasetId,
            {
              page: 1,
              search: "",
              sortColumn: "",
              descending: false,
              filterColumn: "",
              filterValue: "",
            },
            sessionToken,
            controller.signal,
          ),
          getLatestSemanticMapping(
            sessionToken,
            workspaceId,
            projectId,
            datasetId,
          ),
        ]);

        if (!active) {
          return;
        }

        setState({
          kind: "ready",
          dataset,
          columns: preview.columns,
          rows: preview.rows,
          mapping,
          draft: draftFromMapping(mapping),
        });
      } catch {
        if (active && !controller.signal.aborted) {
          setState({
            kind: "error",
            message:
              "We couldn't load the semantic mapping experience. Please try again.",
          });
        }
      }
    }

    void load(token);

    return () => {
      active = false;
      controller.abort();
    };
  }, [
    workspaceId,
    projectId,
    datasetId,
  ]);

  if (state.kind === "loading") {
    return (
      <main className="semantic-mapping-shell">
        <section
          className="semantic-mapping-surface"
          aria-labelledby="semantic-mapping-heading"
        >
          <h1 id="semantic-mapping-heading">
            Semantic Mapping
          </h1>
          <p role="status">
            Loading dataset and column information…
          </p>
        </section>
      </main>
    );
  }

  if (state.kind === "error") {
    return (
      <main className="semantic-mapping-shell">
        <section
          className="semantic-mapping-surface"
          aria-labelledby="semantic-mapping-heading"
        >
          <h1 id="semantic-mapping-heading">
            Semantic Mapping
          </h1>
          <p role="alert">
            {state.message}
          </p>
        </section>
      </main>
    );
  }

  if (state.kind === "blocked") {
    if (state.dataset.status === "validating") {
      return (
        <main className="semantic-mapping-shell">
          <section
          className="semantic-mapping-surface"
          aria-labelledby="semantic-mapping-heading"
        >
            <h1 id="semantic-mapping-heading">
              Semantic Mapping
            </h1>
            <p role="alert">
              This dataset is still being validated. Mapping will be available when validation completes.
            </p>
          </section>
        </main>
      );
    }

    if (state.dataset.status === "pending_upload") {
      return (
        <main className="semantic-mapping-shell">
          <section
          className="semantic-mapping-surface"
          aria-labelledby="semantic-mapping-heading"
        >
            <h1 id="semantic-mapping-heading">
              Semantic Mapping
            </h1>
            <p role="alert">
              This dataset upload has not completed. Mapping will be available after the upload and validation finish.
            </p>
          </section>
        </main>
      );
    }

    if (state.dataset.status === "uploaded") {
      return (
        <main className="semantic-mapping-shell">
          <section
          className="semantic-mapping-surface"
          aria-labelledby="semantic-mapping-heading"
        >
            <h1 id="semantic-mapping-heading">
              Semantic Mapping
            </h1>
            <p role="alert">
              This dataset is waiting for validation. Mapping will be available when validation completes.
            </p>
          </section>
        </main>
      );
    }

    return (
      <main className="semantic-mapping-shell">
        <section
          className="semantic-mapping-surface"
          aria-labelledby="semantic-mapping-heading"
        >
          <h1 id="semantic-mapping-heading">
            Semantic Mapping
          </h1>
          <p role="alert">
            This dataset failed validation. Correct the dataset before configuring semantic mapping.
          </p>
        </section>
      </main>
    );
  }

  function updateTimeColumn(
    timeColumn: string,
  ): void {
    setStepError(null);

    setState((current) => {
      if (current.kind !== "ready") {
        return current;
      }

      return {
        ...current,
        draft: {
          ...current.draft,
          time_column: timeColumn,
        },
      };
    });
  }

  function continueFromTimeStep(): void {
    if (state.kind !== "ready") {
      return;
    }

    const selectedColumn = state.columns.find(
      (column) =>
        column.name === state.draft.time_column,
    );

    if (
      selectedColumn === undefined
      || !isValidTimeColumn(selectedColumn)
    ) {
      setStepError(
        "Choose a valid time column before continuing.",
      );
      return;
    }

    setStepError(null);
    setStep(2);
  }

  function updateUnitColumn(
    unitColumn: string,
  ): void {
    setStepError(null);

    setState((current) => {
      if (current.kind !== "ready") {
        return current;
      }

      return {
        ...current,
        draft: {
          ...current.draft,
          unit_column: unitColumn,
        },
      };
    });
  }

  function continueFromUnitStep(): void {
    if (state.kind !== "ready") {
      return;
    }

    const selectedColumn = state.columns.find(
      (column) =>
        column.name === state.draft.unit_column,
    );

    if (
      selectedColumn === undefined
      || !isValidUnitColumn(selectedColumn)
    ) {
      setStepError(
        "Choose a valid unit column before continuing.",
      );
      return;
    }

    setStepError(null);
    setStep(3);
  }

  function updateTreatmentColumn(
    treatmentColumn: string,
  ): void {
    setStepError(null);

    setState((current) => {
      if (current.kind !== "ready") {
        return current;
      }

      return {
        ...current,
        draft: {
          ...current.draft,
          treatment_column: treatmentColumn,
          treatment_value: "",
          control_value: "",
        },
      };
    });
  }

  function updateTreatmentValue(
    treatmentValue: string,
  ): void {
    setStepError(null);

    setState((current) => {
      if (current.kind !== "ready") {
        return current;
      }

      return {
        ...current,
        draft: {
          ...current.draft,
          treatment_value: treatmentValue,
        },
      };
    });
  }

  function updateControlValue(
    controlValue: string,
  ): void {
    setStepError(null);

    setState((current) => {
      if (current.kind !== "ready") {
        return current;
      }

      return {
        ...current,
        draft: {
          ...current.draft,
          control_value: controlValue,
        },
      };
    });
  }

  function continueFromTreatmentStep(): void {
    if (state.kind !== "ready") {
      return;
    }

    const selectedColumn = state.columns.find(
      (column) =>
        column.name === state.draft.treatment_column,
    );

    const treatmentColumnIsAssigned =
      state.draft.treatment_column
      === state.draft.time_column
      || state.draft.treatment_column
      === state.draft.unit_column;

    if (
      selectedColumn === undefined
      || !isValidTreatmentColumn(selectedColumn)
      || treatmentColumnIsAssigned
    ) {
      setStepError(
        "Choose a valid treatment column before continuing.",
      );
      return;
    }

    const treatmentValue =
      state.draft.treatment_value.trim();
    const controlValue =
      state.draft.control_value.trim();

    if (
      treatmentValue.length === 0
      || controlValue.length === 0
    ) {
      setStepError(
        "Enter both Treatment and Control values before continuing.",
      );
      return;
    }

    if (
      treatmentValue.toLocaleLowerCase()
      === controlValue.toLocaleLowerCase()
    ) {
      setStepError(
        "Treatment and Control values must be different.",
      );
      return;
    }

    setStepError(null);
    setStep(4);
  }

  function updateOutcomeColumn(
    outcomeColumn: string,
  ): void {
    setStepError(null);

    setState((current) => {
      if (current.kind !== "ready") {
        return current;
      }

      return {
        ...current,
        draft: {
          ...current.draft,
          outcome_column: outcomeColumn,
        },
      };
    });
  }

  function continueFromOutcomeStep(): void {
    if (state.kind !== "ready") {
      return;
    }

    const selectedColumn = state.columns.find(
      (column) =>
        column.name === state.draft.outcome_column,
    );

    const outcomeColumnIsAssigned =
      state.draft.outcome_column
      === state.draft.time_column
      || state.draft.outcome_column
      === state.draft.unit_column
      || state.draft.outcome_column
      === state.draft.treatment_column;

    if (
      selectedColumn === undefined
      || !isValidOutcomeColumn(selectedColumn)
      || outcomeColumnIsAssigned
    ) {
      setStepError(
        "Choose a valid outcome column before continuing.",
      );
      return;
    }

    setStepError(null);
    setStep(5);
  }

  function updateSpendColumn(
    spendColumn: string,
  ): void {
    setStepError(null);

    setState((current) => {
      if (current.kind !== "ready") {
        return current;
      }

      return {
        ...current,
        draft: {
          ...current.draft,
          spend_column:
            spendColumn.length === 0
              ? null
              : spendColumn,
        },
      };
    });
  }

  function updateCovariateColumns(
    covariateColumns: string[],
  ): void {
    setStepError(null);

    setState((current) => {
      if (current.kind !== "ready") {
        return current;
      }

      const assignedColumns = new Set([
        current.draft.time_column,
        current.draft.unit_column,
        current.draft.treatment_column,
        current.draft.outcome_column,
        current.draft.spend_column,
      ]);

      const availableColumns = new Set(
        current.columns.map(
          (column) => column.name,
        ),
      );

      const uniqueCovariates = Array.from(
        new Set(covariateColumns),
      ).filter(
        (columnName) =>
          availableColumns.has(columnName)
          && !assignedColumns.has(columnName),
      );

      return {
        ...current,
        draft: {
          ...current.draft,
          covariate_columns:
            uniqueCovariates,
        },
      };
    });
  }

  function continueFromSpendAndCovariatesStep(): void {
    if (state.kind !== "ready") {
      return;
    }

    const validationError =
      validateSemanticMappingDraft(
        state.draft,
        state.columns,
      );

    if (validationError !== null) {
      setStepError(
        validationError,
      );
      return;
    }

    setStepError(null);
    setStep(6);
  }

  const treatmentValueSuggestions =
    observedColumnValues(
      state.rows,
      state.draft.treatment_column,
    );

  async function saveMapping(): Promise<void> {
    if (
      state.kind !== "ready"
      || saveState.kind === "saving"
    ) {
      return;
    }

    const token = window.localStorage.getItem(
      SESSION_TOKEN_KEY,
    );

    if (!token) {
      setSaveState({
        kind: "error",
        message:
          "Your session is no longer available. Please sign in again.",
      });
      return;
    }

    setSaveState({
      kind: "saving",
    });

    try {
      const savedMapping =
        await createSemanticMapping(
          token,
          workspaceId,
          projectId,
          datasetId,
          state.draft,
        );

      setState((current) => {
        if (current.kind !== "ready") {
          return current;
        }

        return {
          ...current,
          mapping: savedMapping,
          draft:
            draftFromMapping(
              savedMapping,
            ),
        };
      });

      setSaveState({
        kind: "success",
        version: savedMapping.version,
      });
    } catch (error) {
      setSaveState({
        kind: "error",
        message:
          error instanceof Error
            ? error.message
            : "Semantic mapping could not be saved.",
      });
    }
  }

  return (
    <main className="semantic-mapping-shell">
      <section
          className="semantic-mapping-surface"
          aria-labelledby="semantic-mapping-heading"
        >
        <header className="semantic-mapping-header">
          <h1 id="semantic-mapping-heading">
            Semantic Mapping
          </h1>
          <p>
            Step {step} of 6
          </p>

          {state.mapping !== null ? (
            <p>
              Editing semantic mapping version {state.mapping.version}.
            </p>
          ) : null}
        </header>

        <nav
          className="semantic-mapping-steps"
          aria-label="Semantic Mapping steps"
        >
          <ol>
            {SEMANTIC_MAPPING_STEPS.map(
              (wizardStep) => (
                <li
                  key={wizardStep.number}
                  aria-current={
                    step === wizardStep.number
                      ? "step"
                      : undefined
                  }
                  className={
                    step === wizardStep.number
                      ? "is-current"
                      : step > wizardStep.number
                        ? "is-complete"
                        : undefined
                  }
                >
                  <span aria-hidden="true">
                    {wizardStep.number}
                  </span>
                  <strong>
                    {wizardStep.label}
                  </strong>
                </li>
              ),
            )}
          </ol>
        </nav>

        <nav
          className="semantic-mapping-dataset-nav"
          aria-label="Dataset navigation"
        >
          <Link
            href={datasetExplorePath(
              workspaceId,
              projectId,
              datasetId,
            )}
          >
            Explore Dataset
          </Link>

          <Link
            href={datasetQualityPath(
              workspaceId,
              projectId,
              datasetId,
            )}
          >
            View Data Quality
          </Link>
        </nav>

        {step === 1 ? (
          <section
            className="semantic-mapping-card"
            aria-labelledby="time-identification-heading"
          >
            <h2 id="time-identification-heading">
              Time Identification
            </h2>

            <p>
              Choose the column that represents when each observation occurred.
            </p>

            <label htmlFor="semantic-time-column">
              Time column
            </label>

            <select
              id="semantic-time-column"
              aria-label="Time column"
              value={state.draft.time_column}
              onChange={(event) =>
                updateTimeColumn(event.target.value)}
            >
              <option value="">
                Select a column
              </option>

              {state.columns.map((column) => (
                <option
                  key={column.name}
                  value={column.name}
                  disabled={
                    !isValidTimeColumn(column)
                    || isColumnAssignedElsewhere(
                      state.draft,
                      column.name,
                      "time_column",
                    )
                  }
                >
                  {column.name} — {column.inferred_type}
                </option>
              ))}
            </select>

            {stepError !== null ? (
              <p role="alert">
                {stepError}
              </p>
            ) : null}

            <button
              type="button"
              onClick={continueFromTimeStep}
            >
              Next
            </button>
          </section>
        ) : step === 2 ? (
          <section
            className="semantic-mapping-card"
            aria-labelledby="unit-identification-heading"
          >
            <h2 id="unit-identification-heading">
              Unit Identification
            </h2>

            <p>
              Choose the column that identifies the unit being measured.
            </p>

            <label htmlFor="semantic-unit-column">
              Unit column
            </label>

            <select
              id="semantic-unit-column"
              aria-label="Unit column"
              value={state.draft.unit_column}
              onChange={(event) =>
                updateUnitColumn(event.target.value)}
            >
              <option value="">
                Select a column
              </option>

              {state.columns.map((column) => (
                <option
                  key={column.name}
                  value={column.name}
                  disabled={
                    !isValidUnitColumn(column)
                    || isColumnAssignedElsewhere(
                      state.draft,
                      column.name,
                      "unit_column",
                    )
                  }
                >
                  {column.name} — {column.inferred_type}
                </option>
              ))}
            </select>

            {stepError !== null ? (
              <p role="alert">
                {stepError}
              </p>
            ) : null}

            <button
              type="button"
              onClick={() => {
                setStepError(null);
                setStep(1);
              }}
            >
              Back
            </button>

            <button
              type="button"
              onClick={continueFromUnitStep}
            >
              Next
            </button>
          </section>
        ) : step === 3 ? (
          <section
            className="semantic-mapping-card"
            aria-labelledby="treatment-identification-heading"
          >
            <h2 id="treatment-identification-heading">
              Treatment Identification
            </h2>

            <p>
              Choose the column that identifies treatment assignment.
            </p>

            <label htmlFor="semantic-treatment-column">
              Treatment column
            </label>

            <select
              id="semantic-treatment-column"
              aria-label="Treatment column"
              value={state.draft.treatment_column}
              onChange={(event) =>
                updateTreatmentColumn(
                  event.target.value,
                )}
            >
              <option value="">
                Select a column
              </option>

              {state.columns.map((column) => (
                <option
                  key={column.name}
                  value={column.name}
                  disabled={
                    !isValidTreatmentColumn(column)
                    || isColumnAssignedElsewhere(
                      state.draft,
                      column.name,
                      "treatment_column",
                    )
                  }
                >
                  {column.name} — {column.inferred_type}
                </option>
              ))}
            </select>

            <label htmlFor="semantic-treatment-value">
              Treatment value
            </label>

            <input
              id="semantic-treatment-value"
              aria-label="Treatment value"
              type="text"
              list="semantic-treatment-values"
              value={state.draft.treatment_value}
              onChange={(event) =>
                updateTreatmentValue(
                  event.target.value,
                )}
            />

            <label htmlFor="semantic-control-value">
              Control value
            </label>

            <input
              id="semantic-control-value"
              aria-label="Control value"
              type="text"
              list="semantic-treatment-values"
              value={state.draft.control_value}
              onChange={(event) =>
                updateControlValue(
                  event.target.value,
                )}
            />

            <datalist id="semantic-treatment-values">
              {treatmentValueSuggestions.map(
                (value) => (
                  <option
                    key={value}
                    value={value}
                  />
                ),
              )}
            </datalist>

            {stepError !== null ? (
              <p role="alert">
                {stepError}
              </p>
            ) : null}

            <button
              type="button"
              onClick={() => {
                setStepError(null);
                setStep(2);
              }}
            >
              Back
            </button>

            <button
              type="button"
              onClick={continueFromTreatmentStep}
            >
              Next
            </button>
          </section>
        ) : step === 4 ? (
          <section
            className="semantic-mapping-card"
            aria-labelledby="outcome-identification-heading"
          >
            <h2 id="outcome-identification-heading">
              Outcome Identification
            </h2>

            <p>
              Choose the numeric column that represents the outcome being measured.
            </p>

            <label htmlFor="semantic-outcome-column">
              Outcome column
            </label>

            <select
              id="semantic-outcome-column"
              aria-label="Outcome column"
              value={state.draft.outcome_column}
              onChange={(event) =>
                updateOutcomeColumn(
                  event.target.value,
                )}
            >
              <option value="">
                Select a column
              </option>

              {state.columns.map((column) => (
                <option
                  key={column.name}
                  value={column.name}
                  disabled={
                    !isValidOutcomeColumn(column)
                    || isColumnAssignedElsewhere(
                      state.draft,
                      column.name,
                      "outcome_column",
                    )
                  }
                >
                  {column.name} — {column.inferred_type}
                </option>
              ))}
            </select>

            {stepError !== null ? (
              <p role="alert">
                {stepError}
              </p>
            ) : null}

            <button
              type="button"
              onClick={() => {
                setStepError(null);
                setStep(3);
              }}
            >
              Back
            </button>

            <button
              type="button"
              onClick={continueFromOutcomeStep}
            >
              Next
            </button>
          </section>
        ) : step === 5 ? (
          <section
            className="semantic-mapping-card"
            aria-labelledby="spend-covariates-heading"
          >
            <h2 id="spend-covariates-heading">
              Spend and Covariates
            </h2>

            <p>
              Optionally choose a spend column and additional covariate columns.
            </p>

            <label htmlFor="semantic-spend-column">
              Spend column
            </label>

            <select
              id="semantic-spend-column"
              aria-label="Spend column"
              value={state.draft.spend_column ?? ""}
              onChange={(event) =>
                updateSpendColumn(
                  event.target.value,
                )}
            >
              <option value="">
                No spend column
              </option>

              {state.columns.map((column) => (
                <option
                  key={column.name}
                  value={column.name}
                  disabled={
                    !isValidOutcomeColumn(column)
                    || isColumnAssignedElsewhere(
                      state.draft,
                      column.name,
                      "spend_column",
                    )
                  }
                >
                  {column.name} — {column.inferred_type}
                </option>
              ))}
            </select>

            <div className="semantic-covariate-field">
              <span
                id="semantic-covariate-columns-label"
                className="semantic-covariate-label"
              >
                Covariate columns
              </span>

              <details className="semantic-covariate-dropdown">
                <summary>
                  {state.draft.covariate_columns.length === 0
                    ? "Select covariate columns"
                    : `${state.draft.covariate_columns.length} covariate${
                        state.draft.covariate_columns.length === 1
                          ? ""
                          : "s"
                      } selected`}
                </summary>

                <div
                  className="semantic-covariate-options"
                  role="group"
                  aria-labelledby="semantic-covariate-columns-label"
                >
                  {state.columns.map((column) => {
                    const checked =
                      state.draft.covariate_columns.includes(
                        column.name,
                      );

                    const disabled =
                      isColumnAssignedElsewhere(
                        state.draft,
                        column.name,
                        "covariate_columns",
                      );

                    return (
                      <label
                        key={column.name}
                        className="semantic-covariate-option"
                      >
                        <input
                          type="checkbox"
                          aria-label={
                            `Covariate ${column.name}`
                          }
                          checked={checked}
                          disabled={disabled}
                          onChange={(event) => {
                            const nextColumns =
                              event.target.checked
                                ? [
                                    ...state.draft
                                      .covariate_columns,
                                    column.name,
                                  ]
                                : state.draft
                                    .covariate_columns
                                    .filter(
                                      (candidate) =>
                                        candidate
                                        !== column.name,
                                    );

                            updateCovariateColumns(
                              nextColumns,
                            );
                          }}
                        />

                        <span>
                          {column.name}
                          {" — "}
                          {column.inferred_type}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </details>
            </div>

            {stepError !== null ? (
              <p role="alert">
                {stepError}
              </p>
            ) : null}

            <button
              type="button"
              onClick={() => {
                setStepError(null);
                setStep(4);
              }}
            >
              Back
            </button>

            <button
              type="button"
              onClick={continueFromSpendAndCovariatesStep}
            >
              Next
            </button>
          </section>
        ) : (
          <section
            className="semantic-mapping-card semantic-mapping-review"
            aria-labelledby="review-save-heading"
          >
            <h2 id="review-save-heading">
              Review and Save
            </h2>

            <p>
              Review the exact semantic mapping request before saving.
            </p>

            <pre aria-label="Semantic mapping request">
              {JSON.stringify(
                state.draft,
                null,
                2,
              )}
            </pre>

            {saveState.kind === "success" ? (
              <p role="status">
                Semantic mapping version {saveState.version} saved successfully.
              </p>
            ) : null}

            {saveState.kind === "error" ? (
              <p role="alert">
                {saveState.message}
              </p>
            ) : null}

            <button
              type="button"
              onClick={() => {
                setStepError(null);
                setStep(5);
              }}
              disabled={saveState.kind === "saving"}
            >
              Back
            </button>

            <button
              type="button"
              onClick={() => {
                void saveMapping();
              }}
              disabled={saveState.kind === "saving"}
            >
              Save Mapping
            </button>
          </section>
        )}
      </section>
    </main>
  );
}
