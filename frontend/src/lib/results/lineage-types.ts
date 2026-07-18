export type AnalysisRunLineageResponse = {
  analysis_run_id: string;
  dataset_id: string;
  dataset_checksum_sha256: string;
  dataset_byte_size: number;
  semantic_mapping_id: string;
  semantic_mapping_version: number;
  semantic_mapping_snapshot: Record<string, unknown> | null;
  analysis_period_snapshot: Record<string, unknown> | null;
  analysis_selection_snapshot: Record<string, unknown> | null;
  treatment_control_snapshot: Record<string, unknown> | null;
  estimand_snapshot: Record<string, unknown> | null;
  estimator_type: string;
  estimator_version: string;
  estimator_configuration: Record<string, unknown>;
  random_seed: number;
  application_version: string;
  source_revision: string;
  statistical_library_versions: Record<string, string> | null;
  input_fingerprint_sha256: string;
  created_at: string;
};

export type AnalysisLineageState =
  | { kind: "loading" }
  | { kind: "permission" }
  | { kind: "missing" }
  | { kind: "error" }
  | {
      kind: "ready";
      data: AnalysisRunLineageResponse;
    };
