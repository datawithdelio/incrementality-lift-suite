import { describe, expect, it } from "vitest";

import { projectNextAction } from "../src/lib/projects/next-action";

const empty = {
  latest_dataset_id: null,
  latest_dataset_status: null,
  semantic_mapping_configured: false,
  latest_analysis_run_id: null,
  latest_analysis_run_status: null,
};

describe("project next action", () => {
  it.each([
    [empty, "Add data to continue"],
    [{ ...empty, latest_dataset_id: "dataset-1", latest_dataset_status: "validating" }, "Validation is in progress"],
    [{ ...empty, latest_dataset_id: "dataset-1", latest_dataset_status: "failed" }, "Review the dataset failure"],
    [{ ...empty, latest_dataset_id: "dataset-1", latest_dataset_status: "ready" }, "Map the dataset columns"],
    [{ ...empty, latest_dataset_id: "dataset-1", latest_dataset_status: "ready", semantic_mapping_configured: true }, "Configure the first analysis"],
    [{ ...empty, latest_dataset_id: "dataset-1", latest_dataset_status: "ready", semantic_mapping_configured: true, latest_analysis_run_id: "run-1", latest_analysis_run_status: "running" }, "Analysis is running"],
    [{ ...empty, latest_dataset_id: "dataset-1", latest_dataset_status: "ready", semantic_mapping_configured: true, latest_analysis_run_id: "run-1", latest_analysis_run_status: "succeeded" }, "Review the latest result"],
    [{ ...empty, latest_dataset_id: "dataset-1", latest_dataset_status: "ready", semantic_mapping_configured: true, latest_analysis_run_id: "run-1", latest_analysis_run_status: "failed" }, "Review the analysis failure"],
  ])("derives persisted state %#", (workflow, title) => {
    expect(projectNextAction(workflow).title).toBe(title);
  });
});
