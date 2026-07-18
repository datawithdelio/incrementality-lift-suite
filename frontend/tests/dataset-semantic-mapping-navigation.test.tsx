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

import {
  ExplorerClient,
} from "@/components/data-products/data-product-clients";
import {
  DataQualityClient,
} from "@/components/data-products/data-quality-client";

const {
  useDataQualityMock,
  useDatasetExplorerMock,
} = vi.hoisted(() => ({
  useDataQualityMock: vi.fn(),
  useDatasetExplorerMock: vi.fn(),
}));

vi.mock(
  "@/lib/data-products/use-data-products",
  () => ({
    useDataQuality: useDataQualityMock,
    useDatasetExplorer:
      useDatasetExplorerMock,
    useReports: vi.fn(),
  }),
);

describe(
  "dataset Semantic Mapping navigation",
  () => {
    beforeEach(() => {
      useDatasetExplorerMock.mockReturnValue({
        state: {
          kind: "ready",
          data: {
            page: 1,
            total_pages: 1,
            total_rows: 1,
            date_range: null,
            columns: [],
            rows: [
              {
                sample: "value",
              },
            ],
            treatment_distribution: {},
            outcome_distribution: {},
          },
        },
        quality: undefined,
        versions: [
          {
            id: "dataset-1",
            source_filename: "data.csv",
            created_at:
              "2026-07-18T12:00:00Z",
          },
        ],
        dataset: undefined,
      });

      useDataQualityMock.mockReturnValue({
        state: {
          kind: "ready",
          data: {
            score: 100,
            ready: true,
            findings: [],
          },
        },
        dataset: {
          id: "dataset-1",
          status: "ready",
        },
      });
    });

    afterEach(() => {
      cleanup();
      vi.clearAllMocks();
    });

    it("links from Data Explorer to the scoped Semantic Mapping page", () => {
      render(
        <ExplorerClient
          workspaceId="workspace-1"
          projectId="project-1"
          datasetId="dataset-1"
        />,
      );

      expect(
        screen.getByRole("link", {
          name: "Semantic Mapping",
        }),
      ).toHaveAttribute(
        "href",
        "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/mapping",
      );
    });

    it("links from Data Quality to the scoped Semantic Mapping page", () => {
      render(
        <DataQualityClient
          workspaceId="workspace-1"
          projectId="project-1"
          datasetId="dataset-1"
        />,
      );

      expect(
        screen.getByRole("link", {
          name: "Semantic Mapping",
        }),
      ).toHaveAttribute(
        "href",
        "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/mapping",
      );
    });
  },
);
