import {
  cleanup,
  render,
  screen,
} from "@testing-library/react";
import {
  afterEach,
  describe,
  expect,
  it,
} from "vitest";

import {
  AnalysisRunStatusExperience,
} from "../src/components/analysis-runs/analysis-run-status-experience";

import type {
  AnalysisResultResponse,
} from "../src/lib/results/types";

const base: AnalysisResultResponse = {
  analysis_run_id: "run-1",
  workspace_id: "workspace-1",
  project_id: "project-1",
  run_status: "succeeded",
  lifecycle_status: "succeeded",
  estimator_type:
    "difference_in_differences",
  estimator_version: "did-v2",
  analysis_configuration: {
    analysis_start_date:
      "2026-01-01",
    analysis_end_date:
      "2026-03-31",
    intervention_date:
      "2026-02-01",
  },
  attempt_count: 1,
  max_attempts: 3,
  failure_information: null,
  result: {
    effect_estimate: 8.2,
    standard_error: 1.9,
    confidence_interval: {
      low: 4.4,
      high: 12,
      confidence_level: 0.95,
    },
    p_value: 0.004,
    sample_size: 240,
    estimator_version: "did-v2",
    library_name: "statsmodels",
    library_version: "0.14.5",
    technical_diagnostics: {},
    business_impact: {
      incremental_outcome: 984,
      relative_lift: 0.082,
      incremental_revenue: null,
      incremental_conversions: null,
    },
    created_at:
      "2026-07-19T16:00:00Z",
  },
};

afterEach(cleanup);

describe(
  "AnalysisRunStatusExperience",
  () => {
    it(
      "shows completed status with scoped View Results and lineage actions",
      () => {
        render(
          <AnalysisRunStatusExperience
            state={{
              kind: "ready",
              refreshError: false,
              data: base,
            }}
          />,
        );

        expect(
          screen.getByRole(
            "heading",
            {
              name: "Analysis complete",
            },
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByRole(
            "link",
            {
              name: "View Results",
            },
          ),
        ).toHaveAttribute(
          "href",
          "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1/result",
        );

        expect(
          screen.getByRole(
            "link",
            {
              name: "View Reproducibility",
            },
          ),
        ).toHaveAttribute(
          "href",
          "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1/lineage",
        );
      },
    );

    it(
      "shows a safe failed-analysis explanation and real attempt count",
      () => {
        render(
          <AnalysisRunStatusExperience
            state={{
              kind: "ready",
              refreshError: false,
              data: {
                ...base,
                run_status: "failed",
                lifecycle_status: "failed",
                attempt_count: 3,
                max_attempts: 3,
                failure_information:
                  "Analysis could not be completed. Review the design and try again.",
                result: null,
              },
            }}
          />,
        );

        expect(
          screen.getByRole(
            "heading",
            {
              name: "Analysis failed",
            },
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByRole("alert"),
        ).toHaveTextContent(
          "Analysis could not be completed. Review the design and try again.",
        );

        expect(
          screen.getByText(
            "Attempt 3 of 3",
          ),
        ).toBeInTheDocument();

        expect(
          screen.queryByText(
            /traceback|database|storage credential/i,
          ),
        ).not.toBeInTheDocument();
      },
    );


    it.each([
      ["queued", "queued", "Analysis queued"],
      ["running", "running", "Analysis running"],
      ["running", "retrying", "Retrying analysis"],
      ["cancelled", "cancelled", "Analysis cancelled"],
    ] as const)(
      "renders the real %s lifecycle as %s",
      (
        runStatus,
        lifecycleStatus,
        expectedHeading,
      ) => {
        render(
          <AnalysisRunStatusExperience
            state={{
              kind: "ready",
              refreshError: false,
              data: {
                ...base,
                run_status: runStatus,
                lifecycle_status:
                  lifecycleStatus,
                result: null,
              },
            }}
          />,
        );

        expect(
          screen.getByRole(
            "heading",
            {
              name:
                expectedHeading,
            },
          ),
        ).toBeInTheDocument();
      },
    );

    it(
      "shows the persisted immutable analysis configuration as read only",
      () => {
        render(
          <AnalysisRunStatusExperience
            state={{
              kind: "ready",
              refreshError: false,
              data: {
                ...base,
                run_status: "queued",
                lifecycle_status:
                  "queued",
                result: null,
              },
            }}
          />,
        );

        expect(
          screen.getByText(
            "Difference in differences",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "2026-01-01",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "2026-03-31",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "2026-02-01",
          ),
        ).toBeInTheDocument();

        expect(
          screen.queryByRole(
            "button",
            {
              name: /edit configuration/i,
            },
          ),
        ).not.toBeInTheDocument();
      },
    );


    it(
      "shows persisted run metadata on the status page",
      () => {
        render(
          <AnalysisRunStatusExperience
            state={{
              kind: "ready",
              refreshError: false,
              data: {
                ...base,
                dataset_id:
                  "00000000-0000-0000-0000-000000000123",
                semantic_mapping_version: 4,
                created_at:
                  "2026-07-19T16:00:00Z",
                started_at: null,
                completed_at: null,
                run_status: "queued",
                lifecycle_status:
                  "queued",
                result: null,
              },
            }}
          />,
        );

        expect(
          screen.getByText(
            "00000000-0000-0000-0000-000000000123",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "Mapping version 4",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            /Jul.*19.*2026/i,
          ),
        ).toBeInTheDocument();
      },
    );

    it(
      "does not offer View Results until a succeeded result is actually available",
      () => {
        render(
          <AnalysisRunStatusExperience
            state={{
              kind: "ready",
              refreshError: false,
              data: {
                ...base,
                dataset_id:
                  "00000000-0000-0000-0000-000000000123",
                semantic_mapping_version: 4,
                created_at:
                  "2026-07-19T16:00:00Z",
                started_at:
                  "2026-07-19T16:01:00Z",
                completed_at:
                  "2026-07-19T16:02:00Z",
                run_status: "succeeded",
                lifecycle_status:
                  "succeeded",
                result: null,
              },
            }}
          />,
        );

        expect(
          screen.getByRole(
            "heading",
            {
              name: "Analysis complete",
            },
          ),
        ).toBeInTheDocument();

        expect(
          screen.queryByRole(
            "link",
            {
              name: "View Results",
            },
          ),
        ).not.toBeInTheDocument();

        expect(
          screen.getByText(
            /result is still becoming available/i,
          ),
        ).toBeInTheDocument();
      },
    );


    it(
      "shows persisted completion metadata for a completed analysis",
      () => {
        render(
          <AnalysisRunStatusExperience
            state={{
              kind: "ready",
              refreshError: false,
              data: {
                ...base,
                dataset_id:
                  "00000000-0000-0000-0000-000000000123",
                semantic_mapping_version: 4,
                created_at:
                  "2026-07-19T16:00:00Z",
                started_at:
                  "2026-07-19T16:01:00Z",
                completed_at:
                  "2026-07-19T16:02:00Z",
                run_status: "succeeded",
                lifecycle_status:
                  "succeeded",
              },
            }}
          />,
        );

        expect(
          screen.getByText(
            "00000000-0000-0000-0000-000000000123",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "Mapping version 4",
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByText(
            "Completed",
          ),
        ).toBeInTheDocument();
      },
    );

  },
);
