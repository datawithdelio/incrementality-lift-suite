import {
  describe,
  expect,
  it,
} from "vitest";

import {
  mapAnalysisConfigurationRequest,
  type AnalysisConfigurationDraft,
} from "@/lib/analysis-configuration/request";

describe(
  "analysis estimator version ownership",
  () => {
    it("does not send a client-controlled estimator version", () => {
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
          {
            datasetId:
              "dataset-1",
            semanticMappingVersion: 3,
          },
        );

      expect(
        request,
      ).not.toHaveProperty(
        "estimator_version",
      );
    });
  },
);
