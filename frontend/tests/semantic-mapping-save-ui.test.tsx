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

import { SESSION_TOKEN_KEY } from "@/lib/auth/api";
import { SemanticMappingClient } from "@/components/semantic-mapping/semantic-mapping-client";

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

describe("semantic mapping save experience", () => {
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
      ],
      rows: [
        {
          event_date: "2026-01-01",
          region: "north",
          treated: 1,
          revenue: 100,
        },
        {
          event_date: "2026-01-02",
          region: "south",
          treated: 0,
          revenue: 120,
        },
      ],
      metadata: {},
      date_range: null,
    });

    getLatestSemanticMappingMock.mockResolvedValue(
      null,
    );
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it("saves once, blocks duplicate submission, and shows the saved mapping version", async () => {
    let resolveSave:
      | ((value: unknown) => void)
      | undefined;

    const pendingSave = new Promise(
      (resolve) => {
        resolveSave = resolve;
      },
    );

    createSemanticMappingMock.mockReturnValue(
      pendingSave,
    );

    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    await screen.findByText("Step 1 of 6");

    fireEvent.change(
      screen.getByLabelText("Time column"),
      {
        target: {
          value: "event_date",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    fireEvent.change(
      screen.getByLabelText("Unit column"),
      {
        target: {
          value: "region",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    fireEvent.change(
      screen.getByLabelText("Treatment column"),
      {
        target: {
          value: "treated",
        },
      },
    );

    fireEvent.change(
      screen.getByLabelText("Treatment value"),
      {
        target: {
          value: "1",
        },
      },
    );

    fireEvent.change(
      screen.getByLabelText("Control value"),
      {
        target: {
          value: "0",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    fireEvent.change(
      screen.getByLabelText("Outcome column"),
      {
        target: {
          value: "revenue",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByText("Step 6 of 6"),
    ).toBeInTheDocument();

    const saveButton =
      screen.getByRole("button", {
        name: "Save Mapping",
      });

    fireEvent.click(saveButton);
    fireEvent.click(saveButton);

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
        covariate_columns: [],
        treatment_value: "1",
        control_value: "0",
      },
    );

    expect(saveButton).toBeDisabled();

    resolveSave?.({
      id: "mapping-2",
      dataset_id: "dataset-1",
      created_by_user_id: "user-1",
      version: 2,
      time_column: "event_date",
      unit_column: "region",
      treatment_column: "treated",
      outcome_column: "revenue",
      spend_column: null,
      covariate_columns: [],
      treatment_value: "1",
      control_value: "0",
      created_at:
        "2026-07-18T18:00:00Z",
      updated_at:
        "2026-07-18T18:00:00Z",
    });

    expect(
      await screen.findByText(
        "Semantic mapping version 2 saved successfully.",
      ),
    ).toBeInTheDocument();

    expect(saveButton).not.toBeDisabled();
  });

  it("preserves the reviewed draft after a save error and allows a successful retry", async () => {
    createSemanticMappingMock
      .mockRejectedValueOnce(
        new Error(
          "Outcome column must be numeric.",
        ),
      )
      .mockResolvedValueOnce({
        id: "mapping-1",
        dataset_id: "dataset-1",
        created_by_user_id: "user-1",
        version: 1,
        time_column: "event_date",
        unit_column: "region",
        treatment_column: "treated",
        outcome_column: "revenue",
        spend_column: null,
        covariate_columns: [],
        treatment_value: "1",
        control_value: "0",
        created_at:
          "2026-07-18T18:00:00Z",
        updated_at:
          "2026-07-18T18:00:00Z",
      });

    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    await screen.findByText("Step 1 of 6");

    fireEvent.change(
      screen.getByLabelText("Time column"),
      {
        target: {
          value: "event_date",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    fireEvent.change(
      screen.getByLabelText("Unit column"),
      {
        target: {
          value: "region",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    fireEvent.change(
      screen.getByLabelText("Treatment column"),
      {
        target: {
          value: "treated",
        },
      },
    );

    fireEvent.change(
      screen.getByLabelText("Treatment value"),
      {
        target: {
          value: "1",
        },
      },
    );

    fireEvent.change(
      screen.getByLabelText("Control value"),
      {
        target: {
          value: "0",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    fireEvent.change(
      screen.getByLabelText("Outcome column"),
      {
        target: {
          value: "revenue",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
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

    const expectedRequest = {
      time_column: "event_date",
      unit_column: "region",
      treatment_column: "treated",
      outcome_column: "revenue",
      spend_column: null,
      covariate_columns: [],
      treatment_value: "1",
      control_value: "0",
    };

    expect(
      JSON.parse(
        requestPreview.textContent ?? "",
      ),
    ).toEqual(expectedRequest);

    const saveButton =
      screen.getByRole("button", {
        name: "Save Mapping",
      });

    fireEvent.click(saveButton);

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Outcome column must be numeric.",
    );

    expect(
      JSON.parse(
        requestPreview.textContent ?? "",
      ),
    ).toEqual(expectedRequest);

    expect(saveButton).not.toBeDisabled();

    fireEvent.click(saveButton);

    expect(
      createSemanticMappingMock,
    ).toHaveBeenCalledTimes(2);

    expect(
      createSemanticMappingMock,
    ).toHaveBeenLastCalledWith(
      "session-token",
      "workspace-1",
      "project-1",
      "dataset-1",
      expectedRequest,
    );

    expect(
      await screen.findByText(
        "Semantic mapping version 1 saved successfully.",
      ),
    ).toBeInTheDocument();
  });

});
