export type LifecycleStatus =
  | "queued"
  | "running"
  | "retrying"
  | "succeeded"
  | "failed"
  | "cancelled";

export type AnalysisResultResponse = {
  analysis_run_id: string;
  workspace_id: string;
  project_id: string;
  run_status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  lifecycle_status: LifecycleStatus;
  estimator_type: string;
  estimator_version: string;
  analysis_configuration: Record<string, unknown>;
  attempt_count: number;
  max_attempts: number;
  failure_information: string | null;
  result: null | {
    effect_estimate: number;
    standard_error: number;
    confidence_interval: { low: number; high: number; confidence_level: number };
    p_value: number;
    sample_size: number;
    estimator_version: string;
    library_name: string;
    library_version: string;
    technical_diagnostics: Record<string, unknown>;
    business_impact: {
      incremental_outcome: number | null;
      relative_lift: number | null;
      incremental_revenue: number | null;
      incremental_conversions: number | null;
    };
    created_at: string;
  };
};

export type ResultsState =
  | { kind: "loading" }
  | { kind: "permission" }
  | { kind: "missing" }
  | { kind: "error" }
  | { kind: "ready"; data: AnalysisResultResponse };
