import {
  render,
  screen,
} from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock(
  "../src/components/semantic-mapping/semantic-mapping-client",
  () => ({
    SemanticMappingClient: ({
      workspaceId,
      projectId,
      datasetId,
    }: {
      workspaceId: string;
      projectId: string;
      datasetId: string;
    }) => (
      <div>
        Semantic Mapping Client:
        {workspaceId}/{projectId}/{datasetId}
      </div>
    ),
  }),
);

import Page from "../src/app/workspaces/[workspaceId]/projects/[projectId]/datasets/[datasetId]/mapping/page";

describe("Semantic Mapping route", () => {
  it("restores workspace, project, and dataset scope from direct URL params", async () => {
    const element = await Page({
      params: Promise.resolve({
        workspaceId: "workspace-1",
        projectId: "project-1",
        datasetId: "dataset-1",
      }),
    });

    render(element);

    expect(
      screen.getByText(
        "Semantic Mapping Client:workspace-1/project-1/dataset-1",
      ),
    ).toBeInTheDocument();
  });
});
