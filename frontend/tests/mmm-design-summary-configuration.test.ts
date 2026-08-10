import { describe, expect, it } from "vitest";

import {
  mapAnalysisConfigurationRequest,
  mapAnalysisContextConfiguration,
  type AnalysisConfigurationDraft,
} from "@/lib/analysis-configuration/request";


describe("MMM design-summary canonical configuration", () => {
  it("uses exactly the same period and population serialization as queued runs", () => {
    const draft: AnalysisConfigurationDraft = {
      estimatorType: "marketing_mix_model",
      period: {
        analysisStartDate: "2026-01-05",
        analysisEndDate: "2026-01-19",
        interventionDate: null,
      },
      selection: {
        rowFilters: [
          {
            column: "promotion",
            operator: "equals",
            value: {
              type: "boolean",
              value: true,
            },
          },
        ],
        selectedGeographies: ["north"],
        excludedGeographies: ["south"],
        segmentColumn: "channel_group",
        selectedSegments: ["brand"],
        excludedSegments: ["other"],
      },
      treatmentControl: {
        kind: "not_applicable",
      },
      settings: {
        kind: "marketing_mix_model",
        outcomeKind: "conversions",
        seasonalityPeriod: 52,
        mediaChannels: [
          "search_spend",
          "social_spend",
        ],
        controlColumns: ["sessions"],
        aggregateSpendColumn: "total_spend",
        adstockDecay: {
          search_spend: 0,
          social_spend: 0,
        },
        saturationHalfSpend: {
          search_spend: 50,
          social_spend: 20,
        },
      },
    };

    const queued = mapAnalysisConfigurationRequest(
      draft,
      {
        datasetId: "dataset-1",
        semanticMappingVersion: 7,
      },
    );

    const context = mapAnalysisContextConfiguration(
      draft.period,
      draft.selection,
    );

    expect(context).toEqual({
      analysis_start_date: "2026-01-05",
      analysis_end_date: "2026-01-19",
      row_filters: [
        {
          column: "promotion",
          operator: "equals",
          value: {
            type: "boolean",
            value: true,
          },
        },
      ],
      selected_geographies: ["north"],
      excluded_geographies: ["south"],
      segment_column: "channel_group",
      selected_segments: ["brand"],
      excluded_segments: ["other"],
    });

    for (const [key, value] of Object.entries(context)) {
      expect(queued.configuration[key]).toEqual(value);
    }
  });
});
