import { describe, expect, it } from "vitest";

import { deriveMarketingMixConfiguration } from "@/lib/analysis-configuration/marketing-mix";

describe("Marketing Mix configuration derivation", () => {
  it("separates channel spend, controls, aggregate spend, and mapped outcome", () => {
    const channelNames = [
      "paid_search_spend",
      "social_spend",
      "tv_spend",
      "display_spend",
      "email_spend",
    ];
    const column = (
      name: string,
      inferred_type = "float",
      median = 10,
    ) => ({
      name,
      inferred_type,
      missing_percentage: 0,
      unique_count: 10,
      minimum: 0,
      maximum: 100,
      mean: 10,
      median,
    });

    const result = deriveMarketingMixConfiguration(
      {
        rows: [],
        columns: [
          column("date", "date"),
          column("region", "string"),
          column("conversions"),
          column("paid_search_spend", "float", 10589),
          column("social_spend", "float", 7518),
          column("tv_spend", "float", 9474),
          column("display_spend", "float", 4627),
          column("email_spend", "float", 1934),
          column("total_spend"),
          column("sessions"),
          column("holiday", "boolean"),
          column("promotion", "boolean"),
        ],
        total_rows: 0,
        page: 1,
        page_size: 50,
        total_pages: 0,
        date_range: null,
        treatment_distribution: {},
        outcome_distribution: {},
      },
      {
        id: "mapping-1",
        dataset_id: "dataset-1",
        created_by_user_id: "user-1",
        version: 1,
        time_column: "date",
        unit_column: "region",
        treatment_column: null,
        outcome_column: "conversions",
        spend_column: "total_spend",
        covariate_columns: ["sessions", "holiday", "promotion"],
        treatment_value: null,
        control_value: null,
        created_at: "2026-08-08T00:00:00Z",
        updated_at: "2026-08-08T00:00:00Z",
      },
    );

    expect(result).toEqual({
      mediaChannels: channelNames,
      controlColumns: ["sessions", "holiday", "promotion"],
      aggregateSpendColumn: "total_spend",
      outcomeKind: "conversions",
      saturationHalfSpendDefaults: {
        paid_search_spend: 10589,
        social_spend: 7518,
        tv_spend: 9474,
        display_spend: 4627,
        email_spend: 1934,
      },
    });
  });
});
