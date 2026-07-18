import { describe, expect, it } from "vitest";

import * as datasetRoutes from "../src/lib/datasets/routes";

describe("dataset routes", () => {
  it("builds the scoped Data Quality route centrally", () => {
    const routes = datasetRoutes as typeof datasetRoutes & {
      datasetQualityPath?: (
        workspaceId: string,
        projectId: string,
        datasetId: string,
      ) => string;
    };

    expect(routes.datasetQualityPath).toBeTypeOf("function");

    expect(
      routes.datasetQualityPath?.(
        "workspace-1",
        "project-1",
        "dataset-1",
      ),
    ).toBe(
      "/workspaces/workspace-1/projects/project-1/datasets/dataset-1/quality",
    );
  });
});
