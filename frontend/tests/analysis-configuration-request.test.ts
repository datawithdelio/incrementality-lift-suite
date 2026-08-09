import {
  describe,
  expect,
  it,
} from "vitest";

import {
  mapAnalysisConfigurationRequest,
  type AnalysisConfigurationDraft,
} from "@/lib/analysis-configuration/request";

const commonSelection = {
  rowFilters: [
    {
      column: "revenue",
      operator: "greater_than" as const,
      value: {
        type: "number" as const,
        value: 95,
      },
    },
    {
      column: "segment",
      operator: "is_not_null" as const,
    },
  ],
  selectedGeographies: ["Boston"],
  excludedGeographies: ["Test Market"],
  segmentColumn: "segment",
  selectedSegments: ["Enterprise"],
  excludedSegments: ["Internal"],
};

function runtimeMetadata() {
  return {
    datasetId: "dataset-1",
    semanticMappingVersion: 3,
  };
}

describe(
  "analysis configuration request mapper",
  () => {
    it("maps Difference in Differences without duplicating mapping-derived treatment assignment", () => {
      const draft: AnalysisConfigurationDraft = {
        estimatorType:
          "difference_in_differences",
        period: {
          analysisStartDate:
            "2025-01-01",
          analysisEndDate:
            "2025-03-31",
          interventionDate:
            "2025-02-01",
        },
        selection: commonSelection,
        treatmentControl: {
          kind: "mapped_binary",
        },
        settings: {
          kind:
            "difference_in_differences",
        },
      };

      expect(
        mapAnalysisConfigurationRequest(
          draft,
          runtimeMetadata(),
        ),
      ).toEqual({
        dataset_id: "dataset-1",
        semantic_mapping_version: 3,
        estimator_type:
          "difference_in_differences",
        configuration: {
          analysis_start_date:
            "2025-01-01",
          analysis_end_date:
            "2025-03-31",
          intervention_date:
            "2025-02-01",
          row_filters: [
            {
              column: "revenue",
              operator:
                "greater_than",
              value: {
                type: "number",
                value: 95,
              },
            },
            {
              column: "segment",
              operator:
                "is_not_null",
            },
          ],
          selected_geographies: [
            "Boston",
          ],
          excluded_geographies: [
            "Test Market",
          ],
          segment_column: "segment",
          selected_segments: [
            "Enterprise",
          ],
          excluded_segments: [
            "Internal",
          ],
        },
      });
    });

    it("maps Synthetic Control treated unit and donor pool", () => {
      const draft: AnalysisConfigurationDraft = {
        estimatorType:
          "synthetic_control",
        period: {
          analysisStartDate:
            "2025-01-01",
          analysisEndDate:
            "2025-03-31",
          interventionDate:
            "2025-02-01",
        },
        selection: {
          ...commonSelection,
          selectedGeographies: [],
          excludedGeographies: [],
        },
        treatmentControl: {
          kind: "synthetic_control",
          treatedUnit: "Boston",
          donorPool: [
            "Chicago",
            "Austin",
          ],
        },
        settings: {
          kind: "synthetic_control",
        },
      };

      const request =
        mapAnalysisConfigurationRequest(
          draft,
          runtimeMetadata(),
        );

      expect(
        request.configuration,
      ).toMatchObject({
        analysis_start_date:
          "2025-01-01",
        analysis_end_date:
          "2025-03-31",
        intervention_date:
          "2025-02-01",
        treated_unit: "Boston",
        donor_pool: [
          "Chicago",
          "Austin",
        ],
      });
    });

    it("maps Geo Holdout assignment and coordinates", () => {
      const draft: AnalysisConfigurationDraft = {
        estimatorType:
          "geo_holdout",
        period: {
          analysisStartDate:
            "2025-01-01",
          analysisEndDate:
            "2025-03-31",
          interventionDate:
            "2025-02-01",
        },
        selection: {
          ...commonSelection,
          selectedGeographies: [],
          excludedGeographies: [],
        },
        treatmentControl: {
          kind: "geo_holdout",
          treatedGeographies: [
            "Boston",
          ],
          controlGeographies: [
            "Chicago",
          ],
        },
        settings: {
          kind: "geo_holdout",
          outcomeKind: "revenue",
          coordinates: {
            Boston: {
              latitude: 42.36,
              longitude: -71.06,
            },
            Chicago: {
              latitude: 41.88,
              longitude: -87.63,
            },
          },
        },
      };

      const request =
        mapAnalysisConfigurationRequest(
          draft,
          runtimeMetadata(),
        );

      expect(
        request.configuration,
      ).toMatchObject({
        treated_geographies: [
          "Boston",
        ],
        control_geographies: [
          "Chicago",
        ],
        outcome_kind: "revenue",
        geo_coordinates: {
          Boston: {
            latitude: 42.36,
            longitude: -71.06,
          },
          Chicago: {
            latitude: 41.88,
            longitude: -87.63,
          },
        },
      });
    });

    it("maps Marketing Mix Modeling settings without treatment fields", () => {
      const draft: AnalysisConfigurationDraft = {
        estimatorType:
          "marketing_mix_model",
        period: {
          analysisStartDate:
            "2025-01-01",
          analysisEndDate:
            "2025-12-31",
          interventionDate: null,
        },
        selection: commonSelection,
        treatmentControl: {
          kind: "not_applicable",
        },
        settings: {
          kind:
            "marketing_mix_model",
          outcomeKind: "revenue",
          seasonalityPeriod: 52,
          mediaChannels: ["paid_search_spend", "social_spend"],
          controlColumns: ["sessions", "holiday", "promotion"],
          aggregateSpendColumn: "total_spend",
          adstockDecay: {
            paid_search_spend: 0.5,
            social_spend: 0.3,
          },
          saturationHalfSpend: {
            paid_search_spend: 20,
            social_spend: 10,
          },
        },
      };

      const request =
        mapAnalysisConfigurationRequest(
          draft,
          runtimeMetadata(),
        );

      expect(
        request.configuration,
      ).toMatchObject({
        analysis_start_date:
          "2025-01-01",
        analysis_end_date:
          "2025-12-31",
        outcome_kind: "revenue",
        seasonality_period: 52,
        media_channels: ["paid_search_spend", "social_spend"],
        control_columns: ["sessions", "holiday", "promotion"],
        aggregate_spend_column: "total_spend",
        adstock_decay: {
          paid_search_spend: 0.5,
          social_spend: 0.3,
        },
        saturation_half_spend: {
          paid_search_spend: 20,
          social_spend: 10,
        },
      });

      expect(
        request.configuration,
      ).not.toHaveProperty(
        "intervention_date",
      );

      expect(
        request.configuration,
      ).not.toHaveProperty(
        "treated_unit",
      );

      expect(
        request.configuration,
      ).not.toHaveProperty(
        "treated_geographies",
      );
    });

    it("maps Off-policy assignment and estimator settings using real backend fields", () => {
      const draft: AnalysisConfigurationDraft = {
        estimatorType:
          "off_policy_evaluation",
        period: {
          analysisStartDate:
            "2025-01-01",
          analysisEndDate:
            "2025-03-31",
          interventionDate: null,
        },
        selection: commonSelection,
        treatmentControl: {
          kind:
            "off_policy_evaluation",
          policyName:
            "growth_policy",
          behaviorPropensityColumn:
            "behavior",
          targetPropensityColumn:
            "target",
        },
        settings: {
          kind:
            "off_policy_evaluation",
          rewardColumn: "reward",
          expectedRewardColumn:
            "prediction",
          primaryMethod:
            "doubly_robust",
        },
      };

      const request =
        mapAnalysisConfigurationRequest(
          draft,
          runtimeMetadata(),
        );

      expect(
        request.configuration,
      ).toMatchObject({
        analysis_start_date:
          "2025-01-01",
        analysis_end_date:
          "2025-03-31",
        policy_name:
          "growth_policy",
        behavior_propensity_column:
          "behavior",
        target_propensity_column:
          "target",
        reward_column: "reward",
        expected_reward_column:
          "prediction",
        primary_method:
          "doubly_robust",
      });

      expect(
        request.configuration,
      ).not.toHaveProperty(
        "intervention_date",
      );
    });

    it("does not send server-owned reproducibility fields", () => {
      const draft: AnalysisConfigurationDraft = {
        estimatorType:
          "difference_in_differences",
        period: {
          analysisStartDate:
            "2025-01-01",
          analysisEndDate:
            "2025-03-31",
          interventionDate:
            "2025-02-01",
        },
        selection: {
          rowFilters: [],
          selectedGeographies: [],
          excludedGeographies: [],
          segmentColumn: "",
          selectedSegments: [],
          excludedSegments: [],
        },
        treatmentControl: {
          kind: "mapped_binary",
        },
        settings: {
          kind:
            "difference_in_differences",
        },
      };

      const request =
        mapAnalysisConfigurationRequest(
          draft,
          runtimeMetadata(),
        );

      expect(request).not.toHaveProperty(
        "random_seed",
      );

      expect(request).not.toHaveProperty(
        "application_version",
      );

      expect(request).not.toHaveProperty(
        "source_revision",
      );

      expect(request).not.toHaveProperty(
        "statistical_library_versions",
      );

      expect(request).not.toHaveProperty(
        "input_fingerprint_sha256",
      );

      expect(request).not.toHaveProperty(
        "analysis_period_snapshot",
      );

      expect(request).not.toHaveProperty(
        "treatment_control_snapshot",
      );
    });
  },
);
