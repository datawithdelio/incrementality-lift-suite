import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  createSemanticMapping,
} from "@/lib/semantic-mapping/api";

describe("semantic mapping save API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POSTs the exact eight-field mapping request to the scoped dataset endpoint", async () => {
    const request = {
      time_column: "event_date",
      unit_column: "region",
      treatment_column: "treated",
      outcome_column: "revenue",
      spend_column: "ad_spend",
      covariate_columns: [
        "competitor_index",
        "holiday_flag",
      ],
      treatment_value: "1",
      control_value: "0",
    };

    const savedMapping = {
      id: "mapping-2",
      dataset_id: "dataset-1",
      created_by_user_id: "user-1",
      version: 2,
      ...request,
      created_at: "2026-07-18T18:00:00Z",
      updated_at: "2026-07-18T18:00:00Z",
    };

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify(savedMapping),
          {
            status: 201,
            headers: {
              "Content-Type": "application/json",
            },
          },
        ),
      );

    const result = await createSemanticMapping(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
      request,
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects/project-1/datasets/dataset-1/semantic-mappings",
      {
        method: "POST",
        headers: {
          Authorization:
            "Bearer session-token",
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify(request),
      },
    );

    expect(result).toEqual(savedMapping);
    expect(result.version).toBe(2);
  });

  it("omits treatment fields from an MMM save", async () => {
    const request = {
      time_column: "event_date",
      unit_column: "region",
      outcome_column: "revenue",
      spend_column: "ad_spend",
      covariate_columns: ["holiday_flag"],
    };
    const savedMapping = {
      id: "mapping-mmm",
      dataset_id: "dataset-1",
      created_by_user_id: "user-1",
      version: 1,
      ...request,
      treatment_column: null,
      treatment_value: null,
      control_value: null,
      created_at: "2026-08-08T18:00:00Z",
      updated_at: "2026-08-08T18:00:00Z",
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify(savedMapping), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      );

    await createSemanticMapping(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
      request,
      "marketing_mix_model",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects/project-1/datasets/dataset-1/semantic-mappings?estimator=marketing_mix_model",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(request),
      }),
    );
  });

  it("surfaces backend 422 validation detail and status", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "Outcome column must be numeric.",
        }),
        {
          status: 422,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    const request = {
      time_column: "event_date",
      unit_column: "region",
      treatment_column: "treated",
      outcome_column: "bad_outcome",
      spend_column: null,
      covariate_columns: [],
      treatment_value: "1",
      control_value: "0",
    };

    await expect(
      createSemanticMapping(
        "session-token",
        "workspace-1",
        "project-1",
        "dataset-1",
        request,
      ),
    ).rejects.toMatchObject({
      message: "Outcome column must be numeric.",
      status: 422,
    });
  });

  it("surfaces backend 409 conflict detail and status", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail:
            "Semantic mapping could not be created because the dataset changed.",
        }),
        {
          status: 409,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    const request = {
      time_column: "event_date",
      unit_column: "region",
      treatment_column: "treated",
      outcome_column: "revenue",
      spend_column: null,
      covariate_columns: [],
      treatment_value: "1",
      control_value: "0",
    };

    await expect(
      createSemanticMapping(
        "session-token",
        "workspace-1",
        "project-1",
        "dataset-1",
        request,
      ),
    ).rejects.toMatchObject({
      message:
        "Semantic mapping could not be created because the dataset changed.",
      status: 409,
    });
  });

});
