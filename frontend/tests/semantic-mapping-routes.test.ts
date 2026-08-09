import { describe, expect, it } from "vitest";

import {
  datasetExplorePath,
  datasetMappingPath,
} from "@/lib/datasets/routes";

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

  it("preserves MMM context across dataset routes", () => {
    expect(
      datasetExplorePath(
        "workspace-123",
        "project-456",
        "dataset-789",
        "marketing_mix_model",
      ),
    ).toContain("?estimator=marketing_mix_model");
    expect(
      datasetMappingPath(
        "workspace-123",
        "project-456",
        "dataset-789",
        "marketing_mix_model",
      ),
    ).toContain("?estimator=marketing_mix_model");
  });
});
