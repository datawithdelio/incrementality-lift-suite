import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  getLatestSemanticMapping,
} from "../src/lib/semantic-mapping/api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("semantic mapping API", () => {
  it("loads the latest mapping using the scoped backend endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "mapping-1",
          dataset_id: "dataset-1",
          created_by_user_id: "user-1",
          version: 3,
          time_column: "date",
          unit_column: "market",
          treatment_column: "treated",
          outcome_column: "revenue",
          spend_column: "spend",
          covariate_columns: [
            "promotion",
            "seasonality",
          ],
          treatment_value: "true",
          control_value: "false",
          created_at: "2026-07-18T12:00:00Z",
          updated_at: "2026-07-18T12:00:00Z",
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const mapping = await getLatestSemanticMapping(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/workspaces/workspace-1/projects/project-1/datasets/dataset-1/semantic-mappings/latest",
      expect.objectContaining({
        method: "GET",
        cache: "no-store",
        headers: expect.objectContaining({
          Authorization: "Bearer session-token",
        }),
      }),
    );

    if (mapping === null) {
      throw new Error(
        "Expected latest semantic mapping response.",
      );
    }

    expect(mapping.version).toBe(3);
    expect(mapping.time_column).toBe("date");
    expect(mapping.covariate_columns).toEqual([
      "promotion",
      "seasonality",
    ]);
  });

  it("returns null when a ready dataset has no semantic mapping yet", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "Semantic mapping is unavailable.",
        }),
        {
          status: 404,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const mapping = await getLatestSemanticMapping(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
    );

    expect(mapping).toBeNull();
  });

});
