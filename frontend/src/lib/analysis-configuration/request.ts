export type AnalysisEstimatorType =
  | "difference_in_differences"
  | "synthetic_control"
  | "geo_holdout"
  | "marketing_mix_model"
  | "off_policy_evaluation";

export type FilterOperator =
  | "equals"
  | "not_equals"
  | "contains"
  | "greater_than"
  | "greater_than_or_equal"
  | "less_than"
  | "less_than_or_equal"
  | "is_null"
  | "is_not_null";

export type FilterValue =
  | {
      type: "string";
      value: string;
    }
  | {
      type: "number";
      value: number;
    }
  | {
      type: "boolean";
      value: boolean;
    }
  | {
      type: "date";
      value: string;
    };

export type FilterRule = {
  column: string;
  operator: FilterOperator;
  value?: FilterValue;
};

export type AnalysisPeriodDraft = {
  analysisStartDate: string;
  analysisEndDate: string;
  interventionDate: string | null;
};

export type AnalysisSelectionDraft = {
  rowFilters: FilterRule[];
  selectedGeographies: string[];
  excludedGeographies: string[];
  segmentColumn: string;
  selectedSegments: string[];
  excludedSegments: string[];
};

export type TreatmentControlDraft =
  | {
      kind: "mapped_binary";
    }
  | {
      kind: "synthetic_control";
      treatedUnit: string;
      donorPool: string[];
    }
  | {
      kind: "geo_holdout";
      treatedGeographies: string[];
      controlGeographies: string[];
    }
  | {
      kind: "not_applicable";
    }
  | {
      kind: "off_policy_evaluation";
      policyName: string;
      behaviorPropensityColumn: string;
      targetPropensityColumn: string;
    };

export type OffPolicyMethod =
  | "importance_sampling"
  | "self_normalized_importance_sampling"
  | "doubly_robust";

export type AnalysisEstimatorSettings =
  | {
      kind: "difference_in_differences";
    }
  | {
      kind: "synthetic_control";
    }
  | {
      kind: "geo_holdout";
      outcomeKind:
        | "outcome"
        | "revenue"
        | "conversions";
      coordinates: Record<
        string,
        {
          latitude: number;
          longitude: number;
        }
      >;
    }
  | {
      kind: "marketing_mix_model";
      outcomeKind:
        | "revenue"
        | "conversions"
        | "outcome";
      seasonalityPeriod: number;
      mediaChannels: string[];
      controlColumns: string[];
      aggregateSpendColumn: string | null;
      adstockDecay: Record<
        string,
        number
      >;
      saturationHalfSpend: Record<
        string,
        number
      >;
    }
  | {
      kind: "off_policy_evaluation";
      rewardColumn: string;
      expectedRewardColumn: string;
      primaryMethod: OffPolicyMethod;
    };

export type AnalysisConfigurationDraft = {
  estimatorType: AnalysisEstimatorType;
  period: AnalysisPeriodDraft;
  selection: AnalysisSelectionDraft;
  treatmentControl: TreatmentControlDraft;
  settings: AnalysisEstimatorSettings;
};

export type AnalysisRequestRuntimeMetadata = {
  datasetId: string;
  semanticMappingVersion: number;
};

export type QueueAnalysisRunRequest = {
  dataset_id: string;
  semantic_mapping_version: number;
  estimator_type: AnalysisEstimatorType;
  configuration: Record<
    string,
    unknown
  >;
};

function mapFilterRule(
  rule: FilterRule,
): Record<string, unknown> {
  return {
    column: rule.column,
    operator: rule.operator,
    ...(rule.value === undefined
      ? {}
      : {
          value: rule.value,
        }),
  };
}

function mapSelection(
  selection: AnalysisSelectionDraft,
): Record<string, unknown> {
  const configuration:
    Record<string, unknown> = {
      row_filters:
        selection.rowFilters.map(
          mapFilterRule,
        ),
      selected_geographies: [
        ...selection
          .selectedGeographies,
      ],
      excluded_geographies: [
        ...selection
          .excludedGeographies,
      ],
  };

  if (
    selection.segmentColumn
      .trim()
      .length > 0
  ) {
    configuration.segment_column =
      selection.segmentColumn;

    configuration.selected_segments = [
      ...selection.selectedSegments,
    ];

    configuration.excluded_segments = [
      ...selection.excludedSegments,
    ];
  }

  return configuration;
}

function mapTreatmentControl(
  treatmentControl:
    TreatmentControlDraft,
): Record<string, unknown> {
  switch (treatmentControl.kind) {
    case "mapped_binary":
    case "not_applicable":
      return {};

    case "synthetic_control":
      return {
        treated_unit:
          treatmentControl.treatedUnit,
        donor_pool: [
          ...treatmentControl
            .donorPool,
        ],
      };

    case "geo_holdout":
      return {
        treated_geographies: [
          ...treatmentControl
            .treatedGeographies,
        ],
        control_geographies: [
          ...treatmentControl
            .controlGeographies,
        ],
      };

    case "off_policy_evaluation":
      return {
        policy_name:
          treatmentControl.policyName,
        behavior_propensity_column:
          treatmentControl
            .behaviorPropensityColumn,
        target_propensity_column:
          treatmentControl
            .targetPropensityColumn,
      };
  }
}

function mapEstimatorSettings(
  settings:
    AnalysisEstimatorSettings,
): Record<string, unknown> {
  switch (settings.kind) {
    case "difference_in_differences":
    case "synthetic_control":
      return {};

    case "geo_holdout":
      return {
        outcome_kind:
          settings.outcomeKind,
        geo_coordinates:
          settings.coordinates,
      };

    case "marketing_mix_model":
      return {
        outcome_kind:
          settings.outcomeKind,
        media_channels: [
          ...settings.mediaChannels,
        ],
        control_columns: [
          ...settings.controlColumns,
        ],
        aggregate_spend_column:
          settings.aggregateSpendColumn,
        seasonality_period:
          settings.seasonalityPeriod,
        adstock_decay:
          settings.adstockDecay,
        saturation_half_spend:
          settings
            .saturationHalfSpend,
      };

    case "off_policy_evaluation":
      return {
        reward_column:
          settings.rewardColumn,
        expected_reward_column:
          settings
            .expectedRewardColumn,
        primary_method:
          settings.primaryMethod,
      };
  }
}

export function mapAnalysisConfigurationRequest(
  draft: AnalysisConfigurationDraft,
  runtime:
    AnalysisRequestRuntimeMetadata,
): QueueAnalysisRunRequest {
  const configuration:
    Record<string, unknown> = {
      analysis_start_date:
        draft.period
          .analysisStartDate,
      analysis_end_date:
        draft.period
          .analysisEndDate,
      ...mapSelection(
        draft.selection,
      ),
      ...mapTreatmentControl(
        draft.treatmentControl,
      ),
      ...mapEstimatorSettings(
        draft.settings,
      ),
  };

  if (
    draft.period.interventionDate
    !== null
    && draft.period
      .interventionDate
      .length > 0
  ) {
    configuration.intervention_date =
      draft.period
        .interventionDate;
  }

  return {
    dataset_id:
      runtime.datasetId,
    semantic_mapping_version:
      runtime
        .semanticMappingVersion,
    estimator_type:
      draft.estimatorType,
    configuration,
  };
}
