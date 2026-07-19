export type ProjectWorkflowState = {
  latest_dataset_id: string | null;
  latest_dataset_status: string | null;
  semantic_mapping_configured: boolean;
  latest_analysis_run_id: string | null;
  latest_analysis_run_status: string | null;
};

export type ProjectNextAction = {
  title: string;
  description: string;
  destination: "dataset" | "analysis" | "configuration" | null;
  stage: 1 | 2 | 3 | 4;
};

export function projectNextAction(workflow: ProjectWorkflowState): ProjectNextAction {
  if (workflow.latest_dataset_id === null) {
    return {
      title: "Add data to continue",
      description: "Connect a dataset to begin validation and semantic mapping.",
      destination: null,
      stage: 2,
    };
  }

  if (workflow.latest_dataset_status === "failed") {
    return {
      title: "Review the dataset failure",
      description: "Inspect the validation evidence, correct the source data, and try again.",
      destination: "dataset",
      stage: 2,
    };
  }

  if (workflow.latest_dataset_status !== "ready") {
    return {
      title: "Validation is in progress",
      description: "The latest dataset is being prepared. Open it to review current progress.",
      destination: "dataset",
      stage: 2,
    };
  }

  if (!workflow.semantic_mapping_configured) {
    return {
      title: "Map the dataset columns",
      description: "Define the time, unit, treatment, and outcome roles before analysis.",
      destination: "dataset",
      stage: 2,
    };
  }

  if (workflow.latest_analysis_run_id === null) {
    return {
      title: "Configure the first analysis",
      description: "The data is ready. Choose a causal method and define the analysis period.",
      destination: "configuration",
      stage: 3,
    };
  }

  if (workflow.latest_analysis_run_status === "succeeded") {
    return {
      title: "Review the latest result",
      description: "Inspect the effect, diagnostics, business impact, and reproducibility receipt.",
      destination: "analysis",
      stage: 4,
    };
  }

  if (["failed", "cancelled", "dead_letter"].includes(workflow.latest_analysis_run_status ?? "")) {
    return {
      title: "Review the analysis failure",
      description: "Open the run for a safe failure explanation and the next recovery step.",
      destination: "analysis",
      stage: 3,
    };
  }

  return {
    title: "Analysis is running",
    description: "The worker is processing the latest run. Open it to follow current status.",
    destination: "analysis",
    stage: 3,
  };
}
