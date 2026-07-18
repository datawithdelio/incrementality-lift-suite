import { describe, expect, it } from "vitest";

import { datasetMappingPath } from "@/lib/datasets/routes";

describe("semantic mapping routes", () => {
  it("builds the workspace, project, and dataset scoped mapping path", () => {
    expect(
      datasetMappingPath(
        "workspace-123",
        "project-456",
        "dataset-789",
      ),
    ).toBe(
      "/workspaces/workspace-123/projects/project-456/datasets/dataset-789/mapping",
    );
  });
});
