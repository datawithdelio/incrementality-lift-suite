import {
  describe,
  expect,
  it,
} from "vitest";

import {
  analysisConfigurationPath,
  analysisRunPath,
} from "../src/lib/projects/routes";

describe(
  "analysis configuration routes",
  () => {
    it("builds the project-scoped new analysis configuration route", () => {
      expect(
        analysisConfigurationPath(
          "workspace-1",
          "project-1",
        ),
      ).toBe(
        "/workspaces/workspace-1/projects/project-1/analyses/new",
      );
    });

    it("builds the scoped analysis run result route", () => {
      expect(
        analysisRunPath(
          "workspace-1",
          "project-1",
          "run-1",
        ),
      ).toBe(
        "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1",
      );
    });
  },
);
