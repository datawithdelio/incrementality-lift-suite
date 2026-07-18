import {
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { SemanticMappingClient } from "@/components/semantic-mapping/semantic-mapping-client";
import { SESSION_TOKEN_KEY } from "@/lib/auth/api";

const {
  createSemanticMappingMock,
  fetchPreviewMock,
  getDatasetMock,
  getLatestSemanticMappingMock,
} = vi.hoisted(() => ({
  createSemanticMappingMock: vi.fn(),
  fetchPreviewMock: vi.fn(),
  getDatasetMock: vi.fn(),
  getLatestSemanticMappingMock: vi.fn(),
}));

vi.mock("@/lib/datasets/api", () => ({
  getDataset: getDatasetMock,
}));

vi.mock("@/lib/data-products/api", () => ({
  fetchPreview: fetchPreviewMock,
}));

vi.mock("@/lib/semantic-mapping/api", () => ({
  createSemanticMapping:
    createSemanticMappingMock,
  getLatestSemanticMapping:
    getLatestSemanticMappingMock,
}));

describe(
  "Semantic Mapping final defensive validation",
  () => {
    beforeEach(() => {
      window.localStorage.setItem(
        SESSION_TOKEN_KEY,
        "session-token",
      );

      getDatasetMock.mockResolvedValue({
        id: "dataset-1",
        workspace_id: "workspace-1",
        project_id: "project-1",
        status: "ready",
      });

      fetchPreviewMock.mockResolvedValue({
        columns: [
          {
            name: "event_date",
            inferred_type: "date",
            missing_percentage: 0,
            unique_count: 10,
            minimum: null,
            maximum: null,
            mean: null,
            median: null,
          },
          {
            name: "region",
            inferred_type: "string",
            missing_percentage: 0,
            unique_count: 5,
            minimum: null,
            maximum: null,
            mean: null,
            median: null,
          },
          {
            name: "cohort",
            inferred_type: "string",
            missing_percentage: 0,
            unique_count: 2,
            minimum: null,
            maximum: null,
            mean: null,
            median: null,
          },
          {
            name: "revenue",
            inferred_type: "float",
            missing_percentage: 0,
            unique_count: 10,
            minimum: 1,
            maximum: 100,
            mean: 50,
            median: 50,
          },
        ],
        rows: [
          {
            event_date: "2026-01-01",
            region: "north",
            cohort: "treated",
            revenue: 100,
          },
          {
            event_date: "2026-01-02",
            region: "south",
            cohort: "control",
            revenue: 90,
          },
        ],
        metadata: {},
        date_range: null,
        treatment_distribution: {},
        outcome_distribution: {},
      });

      // Deliberately stale/invalid persisted payload.
      // All role assignments are otherwise valid, but
      // the backend limits treatment/control values to
      // 255 characters.
      getLatestSemanticMappingMock.mockResolvedValue({
        id: "mapping-1",
        dataset_id: "dataset-1",
        created_by_user_id: "user-1",
        version: 1,
        time_column: "event_date",
        unit_column: "region",
        treatment_column: "cohort",
        outcome_column: "revenue",
        spend_column: null,
        covariate_columns: [],
        treatment_value: "x".repeat(256),
        control_value: "control",
        created_at:
          "2026-07-18T18:00:00Z",
        updated_at:
          "2026-07-18T18:00:00Z",
      });
    });

    afterEach(() => {
      cleanup();
      window.localStorage.clear();
      vi.clearAllMocks();
    });

    it("blocks an invalid stale draft before Review and Save", async () => {
      render(
        <SemanticMappingClient
          workspaceId="workspace-1"
          projectId="project-1"
          datasetId="dataset-1"
        />,
      );

      await screen.findByText(
        "Step 1 of 6",
      );

      // Time
      fireEvent.click(
        screen.getByRole("button", {
          name: "Next",
        }),
      );

      // Unit
      fireEvent.click(
        screen.getByRole("button", {
          name: "Next",
        }),
      );

      // Treatment
      fireEvent.click(
        screen.getByRole("button", {
          name: "Next",
        }),
      );

      // Outcome
      fireEvent.click(
        screen.getByRole("button", {
          name: "Next",
        }),
      );

      expect(
        screen.getByText("Step 5 of 6"),
      ).toBeInTheDocument();

      // Attempt to enter Review and Save.
      fireEvent.click(
        screen.getByRole("button", {
          name: "Next",
        }),
      );

      expect(
        screen.getByRole("alert"),
      ).toHaveTextContent(
        "Treatment value must not exceed 255 characters.",
      );

      expect(
        screen.getByText("Step 5 of 6"),
      ).toBeInTheDocument();

      expect(
        screen.queryByRole("heading", {
          name: "Review and Save",
        }),
      ).not.toBeInTheDocument();

      expect(
        createSemanticMappingMock,
      ).not.toHaveBeenCalled();
    });
  },
);
