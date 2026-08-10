import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchMarketingMixDesignSummary } from "@/lib/data-products/api";


afterEach(() => {
  vi.unstubAllGlobals();
});


describe("fetchMarketingMixDesignSummary", () => {
  it("posts the canonical run configuration and mapping version", async () => {
    const signal = new AbortController().signal;

    const configuration = {
      analysis_start_date: "2026-01-05",
      analysis_end_date: "2026-01-19",
      selected_geographies: ["north"],
      excluded_geographies: [],
      row_filters: [],
      media_channels: ["search_spend", "social_spend"],
      control_columns: ["sessions"],
      aggregate_spend_column: "total_spend",
      outcome_kind: "conversions",
      seasonality_period: 52,
      adstock_decay: {
        search_spend: 0,
        social_spend: 0,
      },
      saturation_half_spend: {
        search_spend: 1,
        social_spend: 1,
      },
    };

    const responseBody = {
      contract_version: "mmm-design-summary-v1",
      period_count: 3,
      saturation_half_spend_defaults: {
        search_spend: 50,
        social_spend: 20,
      },
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => responseBody,
    });

    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchMarketingMixDesignSummary(
      "workspace-1",
      "project-1",
      "dataset-1",
      7,
      configuration,
      "session-token",
      signal,
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];

    expect(url).toBe(
      "/api/v1/workspaces/workspace-1/projects/project-1" +
        "/datasets/dataset-1/marketing-mix-design-summary",
    );

    expect(init.method).toBe("POST");
    expect(init.signal).toBe(signal);

    expect(init.headers).toMatchObject({
      Authorization: "Bearer session-token",
      "Content-Type": "application/json",
    });

    expect(JSON.parse(String(init.body))).toEqual({
      semantic_mapping_version: 7,
      configuration,
    });

    expect(result).toEqual(responseBody);
  });
});
