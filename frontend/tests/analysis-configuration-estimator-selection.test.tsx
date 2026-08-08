import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { SESSION_TOKEN_KEY } from "../src/lib/auth/api";

const {
  fetchPreviewMock,
  getProjectOverviewMock,
  getDatasetMock,
  getLatestSemanticMappingMock,
} = vi.hoisted(() => ({
  fetchPreviewMock: vi.fn(),
  getProjectOverviewMock: vi.fn(),
  getDatasetMock: vi.fn(),
  getLatestSemanticMappingMock: vi.fn(),
}));

vi.mock(
  "../src/lib/data-products/api",
  async () => {
    const actual = await vi.importActual<
      typeof import("../src/lib/data-products/api")
    >("../src/lib/data-products/api");

    return {
      ...actual,
      fetchPreview: fetchPreviewMock,
    };
  },
);

vi.mock(
  "../src/lib/projects/api",
  async () => {
    const actual = await vi.importActual<
      typeof import("../src/lib/projects/api")
    >("../src/lib/projects/api");

    return {
      ...actual,
      getProjectOverview: getProjectOverviewMock,
    };
  },
);

vi.mock(
  "../src/lib/datasets/api",
  async () => {
    const actual = await vi.importActual<
      typeof import("../src/lib/datasets/api")
    >("../src/lib/datasets/api");

    return {
      ...actual,
      getDataset: getDatasetMock,
    };
  },
);

vi.mock(
  "../src/lib/semantic-mapping/api",
  async () => {
    const actual = await vi.importActual<
      typeof import("../src/lib/semantic-mapping/api")
    >("../src/lib/semantic-mapping/api");

    return {
      ...actual,
      getLatestSemanticMapping:
        getLatestSemanticMappingMock,
    };
  },
);

import {
  AnalysisConfigurationClient,
} from "../src/components/analysis-configuration/analysis-configuration-client";

describe(
  "Analysis Configuration estimator selection",
  () => {
    afterEach(() => {
      cleanup();
    });

    beforeEach(() => {
      vi.clearAllMocks();

      window.localStorage.setItem(
        SESSION_TOKEN_KEY,
        "session-token",
      );

      getProjectOverviewMock.mockResolvedValue({
        id: "project-1",
        workspace_id: "workspace-1",
        created_by_user_id: "user-1",
        name: "Lift Study",
        slug: "lift-study",
        description: null,
        status: "active",
        created_at: "2026-07-18T00:00:00Z",
        archived_at: null,
        latest_dataset_id: "dataset-1",
        latest_dataset_status: "ready",
        semantic_mapping_configured: true,
        latest_analysis_run_id: null,
        latest_analysis_run_status: null,
      });

      getDatasetMock.mockResolvedValue({
        id: "dataset-1",
        workspace_id: "workspace-1",
        project_id: "project-1",
        created_by_user_id: "user-1",
        source_filename: "lift.csv",
        storage_key: "datasets/lift.csv",
        media_type: "text/csv",
        byte_size: 1000,
        checksum_sha256: "abc123",
        status: "ready",
        created_at: "2026-07-18T00:00:00Z",
        uploaded_at: "2026-07-18T00:01:00Z",
        validation_started_at: "2026-07-18T00:02:00Z",
        validation_completed_at: "2026-07-18T00:03:00Z",
        row_count: 100,
        column_count: 8,
        failure_reason: null,
      });

      getLatestSemanticMappingMock.mockResolvedValue({
        id: "mapping-1",
        dataset_id: "dataset-1",
        created_by_user_id: "user-1",
        version: 3,
        time_column: "date",
        unit_column: "geo",
        treatment_column: "treated",
        outcome_column: "revenue",
        spend_column: "spend",
        covariate_columns: ["seasonality"],
        treatment_value: "1",
        control_value: "0",
        created_at: "2026-07-18T00:04:00Z",
        updated_at: "2026-07-18T00:04:00Z",
      });

      fetchPreviewMock.mockResolvedValue({
        rows: [],
        columns: [],
        total_rows: 100,
        page: 1,
        page_size: 50,
        total_pages: 2,
        date_range: {
          column: "date",
          minimum: "2025-01-01",
          maximum: "2025-12-31",
        },
        treatment_distribution: {},
        outcome_distribution: {},
      });
    });

    it("shows all five supported analysis methods", async () => {
      render(
        <AnalysisConfigurationClient
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      expect(
        await screen.findByRole(
          "heading",
          {
            name: "Choose an analysis method",
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByRole(
          "button",
          {
            name: /Difference in Differences/i,
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByRole(
          "button",
          {
            name: /Synthetic Control/i,
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByRole(
          "button",
          {
            name: /Geo Holdout/i,
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByRole(
          "button",
          {
            name: /Marketing Mix Modeling/i,
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByRole(
          "button",
          {
            name: /Off-policy Evaluation/i,
          },
        ),
      ).toBeInTheDocument();
    });

    it("explains the ready inputs and method requirements before selection", async () => {
      render(
        <AnalysisConfigurationClient
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      const analysisInputs =
        await screen.findByRole(
          "region",
          {
            name: "Analysis inputs",
          },
        );

      expect(
        within(analysisInputs).getByText(
          "lift.csv",
        ),
      ).toBeInTheDocument();

      expect(
        within(analysisInputs).getByText(
          "Mapping v3",
        ),
      ).toBeInTheDocument();

      expect(
        within(analysisInputs).getByText(
          "Validated and ready",
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByRole("group", {
          name: "Supported analysis methods",
        }),
      ).toBeInTheDocument();

      expect(
        screen.getByText(
          "Treatment and control groups",
        ),
      ).toBeInTheDocument();
    });

    it("requires one estimator selection before continuing", async () => {
      render(
        <AnalysisConfigurationClient
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      const continueButton =
        await screen.findByRole(
          "button",
          {
            name: "Continue",
          },
        );

      expect(
        continueButton,
      ).toBeDisabled();

      const syntheticControl =
        screen.getByRole(
          "button",
          {
            name: /Synthetic Control/i,
          },
        );

      fireEvent.click(
        syntheticControl,
      );

      expect(
        syntheticControl,
      ).toHaveAttribute(
        "aria-pressed",
        "true",
      );

      expect(
        continueButton,
      ).toBeEnabled();
    });
    it("moves treatment-based estimators to an analysis period step", async () => {
      render(
        <AnalysisConfigurationClient
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      const differenceInDifferences =
        await screen.findByRole(
          "button",
          {
            name: /Difference in Differences/i,
          },
        );

      fireEvent.click(
        differenceInDifferences,
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Continue",
          },
        ),
      );

      expect(
        screen.getByRole(
          "heading",
          {
            name: "Define analysis period",
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByLabelText(
          "Analysis start date",
        ),
      ).toHaveAttribute(
        "type",
        "date",
      );

      expect(
        screen.getByLabelText(
          "Intervention date",
        ),
      ).toHaveAttribute(
        "type",
        "date",
      );

      expect(
        screen.getByLabelText(
          "Analysis end date",
        ),
      ).toHaveAttribute(
        "type",
        "date",
      );
    });

    it("does not require an intervention date for Marketing Mix Modeling", async () => {
      render(
        <AnalysisConfigurationClient
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      const marketingMixModeling =
        await screen.findByRole(
          "button",
          {
            name: /Marketing Mix Modeling/i,
          },
        );

      fireEvent.click(
        marketingMixModeling,
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Continue",
          },
        ),
      );

      expect(
        screen.getByRole(
          "heading",
          {
            name: "Define analysis period",
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByLabelText(
          "Analysis start date",
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByLabelText(
          "Analysis end date",
        ),
      ).toBeInTheDocument();

      expect(
        screen.queryByLabelText(
          "Intervention date",
        ),
      ).not.toBeInTheDocument();
    });

    it("requires a valid treatment analysis period before continuing", async () => {
      render(
        <AnalysisConfigurationClient
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      fireEvent.click(
        await screen.findByRole(
          "button",
          {
            name: /Difference in Differences/i,
          },
        ),
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Continue",
          },
        ),
      );

      const periodContinue =
        screen.getByRole(
          "button",
          {
            name: "Continue",
          },
        );

      expect(
        periodContinue,
      ).toBeDisabled();

      fireEvent.change(
        screen.getByLabelText(
          "Analysis start date",
        ),
        {
          target: {
            value: "2025-01-01",
          },
        },
      );

      fireEvent.change(
        screen.getByLabelText(
          "Intervention date",
        ),
        {
          target: {
            value: "2025-02-01",
          },
        },
      );

      fireEvent.change(
        screen.getByLabelText(
          "Analysis end date",
        ),
        {
          target: {
            value: "2025-03-31",
          },
        },
      );

      expect(
        periodContinue,
      ).toBeEnabled();
    });

    it("blocks analysis dates outside the dataset range", async () => {
      render(
        <AnalysisConfigurationClient
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      fireEvent.click(
        await screen.findByRole("button", {
          name: /Synthetic Control/i,
        }),
      );
      fireEvent.click(screen.getByRole("button", { name: "Continue" }));

      fireEvent.change(screen.getByLabelText("Analysis start date"), {
        target: { value: "2024-12-31" },
      });
      fireEvent.change(screen.getByLabelText("Intervention date"), {
        target: { value: "2025-05-25" },
      });
      fireEvent.change(screen.getByLabelText("Analysis end date"), {
        target: { value: "2025-07-27" },
      });

      expect(screen.getByRole("alert")).toHaveTextContent(
        "Analysis start date must be between 2025-01-01 and 2025-12-31.",
      );
      expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
      expect(screen.queryByText("Dates are ready for the next step.")).not.toBeInTheDocument();
    });

    it("rejects an intervention date without a usable pre-period", async () => {
      render(
        <AnalysisConfigurationClient
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      fireEvent.click(
        await screen.findByRole(
          "button",
          {
            name: /Difference in Differences/i,
          },
        ),
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Continue",
          },
        ),
      );

      fireEvent.change(
        screen.getByLabelText(
          "Analysis start date",
        ),
        {
          target: {
            value: "2025-01-01",
          },
        },
      );

      fireEvent.change(
        screen.getByLabelText(
          "Intervention date",
        ),
        {
          target: {
            value: "2025-01-01",
          },
        },
      );

      fireEvent.change(
        screen.getByLabelText(
          "Analysis end date",
        ),
        {
          target: {
            value: "2025-03-31",
          },
        },
      );

      expect(
        screen.getByRole(
          "alert",
        ),
      ).toHaveTextContent(
        "Intervention date must be after the analysis start date and no later than the analysis end date.",
      );

      expect(
        screen.getByRole(
          "button",
          {
            name: "Continue",
          },
        ),
      ).toBeDisabled();
    });

    it("requires only start and end dates for Marketing Mix Modeling", async () => {
      render(
        <AnalysisConfigurationClient
          workspaceId="workspace-1"
          projectId="project-1"
        />,
      );

      fireEvent.click(
        await screen.findByRole(
          "button",
          {
            name: /Marketing Mix Modeling/i,
          },
        ),
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Continue",
          },
        ),
      );

      const periodContinue =
        screen.getByRole(
          "button",
          {
            name: "Continue",
          },
        );

      fireEvent.change(
        screen.getByLabelText(
          "Analysis start date",
        ),
        {
          target: {
            value: "2025-01-01",
          },
        },
      );

      fireEvent.change(
        screen.getByLabelText(
          "Analysis end date",
        ),
        {
          target: {
            value: "2025-03-31",
          },
        },
      );

      expect(
        periodContinue,
      ).toBeEnabled();
    });

  },
);
