export type LoadState<T> =
  | { kind: "loading" }
  | { kind: "permission" }
  | { kind: "error" }
  | { kind: "ready"; data: T };

export type ColumnSummary = {
  name: string;
  inferred_type: string;
  missing_percentage: number;
  unique_count: number;
  minimum: number | string | null;
  maximum: number | string | null;
  mean: number | null;
  median: number | null;
};

export type TrendPoint = {
  period: string;
  treatment_value: number | null;
  control_value: number | null;
  treatment_observations: number;
  control_observations: number;
  phase: "pre" | "post";
};

export type HistogramBin = {
  minimum: number;
  maximum: number;
  treatment_count: number;
  control_count: number;
};

export type OutcomeDistribution = {
  minimum: number | null;
  maximum: number | null;
  mean: number | null;
  median: number | null;
  first_quartile: number | null;
  third_quartile: number | null;
  outlier_count: number;
  sample_size: number;
  bins: HistogramBin[];
};

export type MissingnessPoint = {
  column: string;
  missing_count: number;
  missing_percentage: number;
};

export type TreatmentBalance = {
  treatment_label: string;
  treatment_value: string;
  treatment_count: number;
  treatment_percentage: number;
  control_label: string;
  control_value: string;
  control_count: number;
  control_percentage: number;
  treatment_pre_count: number;
  treatment_post_count: number;
  control_pre_count: number;
  control_post_count: number;
  status: string;
};

export type BreakdownPoint = {
  value: string;
  outcome_mean: number | null;
  observation_count: number;
  treatment_count: number;
  control_count: number;
};

export type DatasetVisualizations = {
  time_column: string | null;
  treatment_column: string | null;
  outcome_column: string | null;
  treatment_start_date: string | null;
  trend: TrendPoint[];
  distribution: OutcomeDistribution;
  missingness: MissingnessPoint[];
  balance: TreatmentBalance | null;
  breakdowns: Record<string, BreakdownPoint[]>;
};

export type DatasetPreview = {
  rows: Record<string, unknown>[];
  columns: ColumnSummary[];
  total_rows: number;
  page: number;
  page_size: number;
  total_pages: number;
  date_range: {
    column: string;
    minimum: string;
    maximum: string;
  } | null;
  treatment_distribution: Record<string, number>;
  outcome_distribution: Record<string, number>;
  visualizations?: DatasetVisualizations;
};

export type GeographyMetrics = {
  outcome_sum: number | null;
  spend_sum: number | null;
  covariate_sums: Record<string, number>;
};

export type GeographySummaryItem = {
  value: string;
  observation_count: number;
  latitude: number | null;
  longitude: number | null;
  coordinate_status: "verified" | "missing";
  metrics: GeographyMetrics;
};

export type GeographySummary = {
  mapping_version: number;
  unit_column: string;
  total_geographies: number;
  geographies: GeographySummaryItem[];
};

export type MarketingMixDesignSummary = {
  contract_version: "mmm-design-summary-v1";
  period_count: number;
  saturation_half_spend_defaults: Record<string, number>;
};

export type QualityFinding = {
  rule_id: string;
  severity: string;
  passed: boolean;
  evidence: Record<string, unknown>;
  recommendation: string;
};

export type DataQuality = {
  score: number;
  ready: boolean;
  findings: QualityFinding[];
};

export type ReportJob = {
  id: string;
  version: number;
  format: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  failure_reason: string | null;
  created_at: string;
};

export type DatasetVersion = {
  id: string;
  source_filename: string;
  checksum_sha256: string;
  row_count: number | null;
  created_at: string;
};
