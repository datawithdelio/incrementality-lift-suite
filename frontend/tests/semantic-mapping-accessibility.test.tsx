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

import { SemanticMappingClient } from "@/components/semantic-mapping/semantic-mapping-client";
import { SESSION_TOKEN_KEY } from "@/lib/auth/api";

const {
  fetchPreviewMock,
  getDatasetMock,
  getLatestSemanticMappingMock,
} = vi.hoisted(() => ({
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
  createSemanticMapping: vi.fn(),
  getLatestSemanticMapping:
    getLatestSemanticMappingMock,
}));

describe(
  "Semantic Mapping accessibility",
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
        ],
        rows: [
          {
            event_date: "2026-01-01",
            region: "north",
          },
        ],
        metadata: {},
        date_range: null,
        treatment_distribution: {},
        outcome_distribution: {},
      });

      getLatestSemanticMappingMock.mockResolvedValue(
        null,
      );
    });

    afterEach(() => {
      cleanup();
      window.localStorage.clear();
      vi.clearAllMocks();
    });

    it("exposes all six wizard steps and identifies the current step accessibly", async () => {
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

      const progress =
        screen.getByRole(
          "navigation",
          {
            name: "Semantic Mapping steps",
          },
        );

      expect(
        within(progress).getAllByRole(
          "listitem",
        ),
      ).toHaveLength(6);

      expect(
        within(progress).getByText(
          "Time",
        ).closest("li"),
      ).toHaveAttribute(
        "aria-current",
        "step",
      );

      expect(
        within(progress).getByText(
          "Unit",
        ).closest("li"),
      ).not.toHaveAttribute(
        "aria-current",
      );

      expect(
        within(progress).getByText(
          "Treatment",
        ),
      ).toBeInTheDocument();

      expect(
        within(progress).getByText(
          "Outcome",
        ),
      ).toBeInTheDocument();

      expect(
        within(progress).getByText(
          "Spend and Covariates",
        ),
      ).toBeInTheDocument();

      expect(
        within(progress).getByText(
          "Review and Save",
        ),
      ).toBeInTheDocument();

      fireEvent.change(
        screen.getByLabelText(
          "Time column",
        ),
        {
          target: {
            value: "event_date",
          },
        },
      );

      fireEvent.click(
        screen.getByRole(
          "button",
          {
            name: "Next",
          },
        ),
      );

      expect(
        within(progress).getByText(
          "Unit",
        ).closest("li"),
      ).toHaveAttribute(
        "aria-current",
        "step",
      );

      expect(
        within(progress).getByText(
          "Time",
        ).closest("li"),
      ).not.toHaveAttribute(
        "aria-current",
      );
    });
  },
);
