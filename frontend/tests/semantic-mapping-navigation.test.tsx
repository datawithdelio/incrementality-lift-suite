import {
  cleanup,
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
  "Semantic Mapping dataset navigation",
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
            unique_count: 1,
            minimum: null,
            maximum: null,
            mean: null,
            median: null,
          },
        ],
        rows: [
          {
            event_date: "2026-01-01",
          },
        ],
        metadata: {},
        date_range: null,
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

    it("links back to the scoped Data Explorer and Data Quality pages", async () => {
      render(
        <SemanticMappingClient
          workspaceId="workspace-1"
          projectId="project-1"
          datasetId="dataset-1"
        />,
      );

      await screen.findByText("Step 1 of 6");

      expect(
        screen.getByRole("link", {
          name: "Explore Dataset",
        }),
      ).toHaveAttribute(
        "href",
        "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/explore",
      );

      expect(
        screen.getByRole("link", {
          name: "View Data Quality",
        }),
      ).toHaveAttribute(
        "href",
        "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/quality",
      );
    });
  },
);
