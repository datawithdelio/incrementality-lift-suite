import {
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { SemanticMappingClient } from "@/components/semantic-mapping/semantic-mapping-client";
import { SESSION_TOKEN_KEY } from "@/lib/auth/api";

const {
  createSemanticMappingMock,
  fetchPreviewMock,
  getDatasetMock,
  getLatestSemanticMappingMock,
} = vi.hoisted(() => ({
  createSemanticMappingMock: vi.fn(),
  fetchPreviewMock: vi.fn(),
  getDatasetMock: vi.fn(),
  getLatestSemanticMappingMock: vi.fn(),
}));

vi.mock("@/lib/datasets/api", () => ({
  getDataset: getDatasetMock,
}));

vi.mock("@/lib/data-products/api", () => ({
  fetchPreview: fetchPreviewMock,
}));

vi.mock("@/lib/semantic-mapping/api", () => ({
  createSemanticMapping:
    createSemanticMappingMock,
  getLatestSemanticMapping:
    getLatestSemanticMappingMock,
}));

describe("existing semantic mapping editing", () => {
  beforeEach(() => {
    window.localStorage.setItem(
      SESSION_TOKEN_KEY,
      "session-token",
    );

    getDatasetMock.mockResolvedValue({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      status: "ready",
    });

    fetchPreviewMock.mockResolvedValue({
      columns: [
        {
          name: "event_date",
          inferred_type: "date",
          missing_percentage: 0,
          unique_count: 100,
          minimum: null,
          maximum: null,
          mean: null,
          median: null,
        },
        {
          name: "region",
          inferred_type: "string",
          missing_percentage: 0,
          unique_count: 10,
          minimum: null,
          maximum: null,
          mean: null,
          median: null,
        },
        {
          name: "treated",
          inferred_type: "integer",
          missing_percentage: 0,
          unique_count: 2,
          minimum: 0,
          maximum: 1,
          mean: 0.5,
          median: 0.5,
        },
        {
          name: "revenue",
          inferred_type: "float",
          missing_percentage: 0,
          unique_count: 100,
          minimum: 10,
          maximum: 500,
          mean: 120,
          median: 100,
        },
        {
          name: "ad_spend",
          inferred_type: "float",
          missing_percentage: 0,
          unique_count: 90,
          minimum: 0,
          maximum: 250,
          mean: 75,
          median: 60,
        },
        {
          name: "competitor_index",
          inferred_type: "float",
          missing_percentage: 0,
          unique_count: 40,
          minimum: 0,
          maximum: 10,
          mean: 4.5,
          median: 4,
        },
        {
          name: "holiday_flag",
          inferred_type: "boolean",
          missing_percentage: 0,
          unique_count: 2,
          minimum: null,
          maximum: null,
          mean: null,
          median: null,
        },
      ],
      rows: [
        {
          event_date: "2026-01-01",
          region: "north",
          treated: 1,
          revenue: 100,
          ad_spend: 40,
          competitor_index: 5,
          holiday_flag: false,
        },
        {
          event_date: "2026-01-02",
          region: "south",
          treated: 0,
          revenue: 120,
          ad_spend: 50,
          competitor_index: 4,
          holiday_flag: true,
        },
      ],
      metadata: {},
      date_range: null,
    });

    getLatestSemanticMappingMock.mockResolvedValue({
      id: "mapping-3",
      dataset_id: "dataset-1",
      created_by_user_id: "user-1",
      version: 3,
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
      created_at:
        "2026-07-18T17:00:00Z",
      updated_at:
        "2026-07-18T17:00:00Z",
    });

    createSemanticMappingMock.mockResolvedValue({
      id: "mapping-4",
      dataset_id: "dataset-1",
      created_by_user_id: "user-1",
      version: 4,
      time_column: "event_date",
      unit_column: "region",
      treatment_column: "treated",
      outcome_column: "revenue",
      spend_column: null,
      covariate_columns: [
        "competitor_index",
        "holiday_flag",
      ],
      treatment_value: "1",
      control_value: "0",
      created_at:
        "2026-07-18T18:00:00Z",
      updated_at:
        "2026-07-18T18:00:00Z",
    });
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it("restores all eight fields and saves edits as a new mapping version", async () => {
    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    await screen.findByText("Step 1 of 6");

    expect(
      screen.getByText(
        "Editing semantic mapping version 3.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Time column"),
    ).toHaveValue("event_date");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByLabelText("Unit column"),
    ).toHaveValue("region");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByLabelText("Treatment column"),
    ).toHaveValue("treated");

    expect(
      screen.getByLabelText("Treatment value"),
    ).toHaveValue("1");

    expect(
      screen.getByLabelText("Control value"),
    ).toHaveValue("0");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByLabelText("Outcome column"),
    ).toHaveValue("revenue");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByLabelText("Spend column"),
    ).toHaveValue("ad_spend");

    const covariates =
      screen.getByLabelText(
        "Covariate columns",
      ) as HTMLSelectElement;

    expect(
      Array.from(
        covariates.selectedOptions,
      ).map(
        (option) => option.value,
      ),
    ).toEqual([
      "competitor_index",
      "holiday_flag",
    ]);

    // Edit the existing mapping.
    fireEvent.change(
      screen.getByLabelText("Spend column"),
      {
        target: {
          value: "",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    const requestPreview =
      screen.getByLabelText(
        "Semantic mapping request",
      );

    expect(
      JSON.parse(
        requestPreview.textContent ?? "",
      ),
    ).toEqual({
      time_column: "event_date",
      unit_column: "region",
      treatment_column: "treated",
      outcome_column: "revenue",
      spend_column: null,
      covariate_columns: [
        "competitor_index",
        "holiday_flag",
      ],
      treatment_value: "1",
      control_value: "0",
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Save Mapping",
      }),
    );

    expect(
      createSemanticMappingMock,
    ).toHaveBeenCalledTimes(1);

    expect(
      createSemanticMappingMock,
    ).toHaveBeenCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
      {
        time_column: "event_date",
        unit_column: "region",
        treatment_column: "treated",
        outcome_column: "revenue",
        spend_column: null,
        covariate_columns: [
          "competitor_index",
          "holiday_flag",
        ],
        treatment_value: "1",
        control_value: "0",
      },
    );

    expect(
      await screen.findByText(
        "Semantic mapping version 4 saved successfully.",
      ),
    ).toBeInTheDocument();
  });
});
