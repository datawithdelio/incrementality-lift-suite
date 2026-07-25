import {
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock(
  "../src/lib/data-products/use-data-products",
  () => ({
    useDatasetExplorer: vi.fn(() => ({
      state: {
        kind: "ready",
        data: {
          rows: [{ market: "Boston" }],
          columns: [],
          total_rows: 1537,
          page: 31,
          page_size: 50,
          total_pages: 31,
          date_range: null,
          treatment_distribution: {},
          outcome_distribution: {},
        },
      },
      quality: undefined,
      versions: [],
      dataset: {
        id: "dataset-1",
        workspace_id: "workspace-1",
        project_id: "project-1",
        created_by_user_id: "user-1",
        source_filename: "campaign-results.csv",
        storage_key: "private/storage/path.csv",
        media_type: "text/csv",
        byte_size: 2048,
        checksum_sha256: "a".repeat(64),
        status: "ready",
        created_at: "2026-07-18T12:00:00Z",
        uploaded_at: "2026-07-18T12:05:00Z",
        validation_started_at: "2026-07-18T12:06:00Z",
        validation_completed_at: "2026-07-18T12:07:00Z",
        row_count: 1537,
        column_count: 13,
        failure_reason: null,
      },
    })),
  }),
);

import { ExplorerClient } from "../src/components/data-products/data-product-clients";

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe("ExplorerClient", () => {
  it("passes restored backend dataset metadata into the Explorer", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByText("campaign-results.csv"),
    ).toBeInTheDocument();

    expect(screen.getByText("1,537")).toBeInTheDocument();
    expect(screen.getByText("13")).toBeInTheDocument();

    expect(
      screen.queryByText("private/storage/path.csv"),
    ).not.toBeInTheDocument();
  });
});

describe("ExplorerClient dataset navigation", () => {
  it("links to the correctly scoped Data Quality page", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
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
});

describe("ExplorerClient pagination", () => {
  it("disables Next when the backend reports the final page", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByRole("button", {
        name: "Next",
      }),
    ).toBeDisabled();
  });
});

describe("ExplorerClient saved views", () => {
  it("saves the current exploration settings under a user-defined name", () => {
    render(
      <ExplorerClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    fireEvent.change(
      screen.getByRole("textbox", {
        name: "Saved view name",
      }),
      {
        target: {
          value: "Missing revenue review",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Save current view",
      }),
    );

    expect(
      screen.getByRole("option", {
        name: "Missing revenue review",
      }),
    ).toBeInTheDocument();
  });
});
