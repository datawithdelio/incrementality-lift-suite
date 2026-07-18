import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock(
  "../src/lib/data-products/use-data-products",
  () => ({
    useDataQuality: vi.fn(() => ({
      state: {
        kind: "ready",
        data: {
          score: 100,
          ready: true,
          findings: [],
        },
      },
    })),
  }),
);

import { DataQualityClient } from "../src/components/data-products/data-quality-client";

afterEach(cleanup);

describe("DataQualityClient", () => {
  it("loads the scoped quality experience with the established default estimator", () => {
    render(
      <DataQualityClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Data Quality",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("combobox", {
        name: "Causal method",
      }),
    ).toHaveValue("difference_in_differences");

    expect(
      screen.getByText("No data-quality issues were found."),
    ).toBeInTheDocument();
  });
});

describe("DataQualityClient dataset navigation", () => {
  it("links back to the correctly scoped Data Explorer", () => {
    render(
      <DataQualityClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      screen.getByRole("link", {
        name: "Explore Dataset",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/explore",
    );
  });
});
