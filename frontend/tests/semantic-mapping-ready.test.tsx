import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const {
  getDatasetMock,
  fetchPreviewMock,
  getLatestSemanticMappingMock,
} = vi.hoisted(() => ({
  getDatasetMock: vi.fn(),
  fetchPreviewMock: vi.fn(),
  getLatestSemanticMappingMock: vi.fn(),
}));

vi.mock(
  "../src/lib/datasets/api",
  async () => {
    const actual = await vi.importActual<
      typeof import("../src/lib/datasets/api")
    >("../src/lib/datasets/api");

    return {
      ...actual,
      getDataset: getDatasetMock,
    };
  },
);

vi.mock(
  "../src/lib/data-products/api",
  async () => {
    const actual = await vi.importActual<
      typeof import("../src/lib/data-products/api")
    >("../src/lib/data-products/api");

    return {
      ...actual,
      fetchPreview: fetchPreviewMock,
    };
  },
);

vi.mock(
  "../src/lib/semantic-mapping/api",
  async () => {
    const actual = await vi.importActual<
      typeof import("../src/lib/semantic-mapping/api")
    >("../src/lib/semantic-mapping/api");

    return {
      ...actual,
      getLatestSemanticMapping:
        getLatestSemanticMappingMock,
    };
  },
);

import { SemanticMappingClient } from "../src/components/semantic-mapping/semantic-mapping-client";

describe("semantic mapping ready dataset experience", () => {
  beforeEach(() => {
    window.localStorage.setItem(
      "incrementality_session_token",
      "session-token",
    );

    getDatasetMock.mockResolvedValue({
      id: "dataset-1",
      workspace_id: "workspace-1",
      project_id: "project-1",
      created_by_user_id: "user-1",
      source_filename: "experiment.csv",
      storage_key: "datasets/experiment.csv",
      media_type: "text/csv",
      byte_size: 100,
      checksum_sha256: "abc123",
      status: "ready",
      created_at: "2026-07-18T12:00:00Z",
      uploaded_at: "2026-07-18T12:01:00Z",
      validation_started_at: "2026-07-18T12:02:00Z",
      validation_completed_at: "2026-07-18T12:03:00Z",
      row_count: 100,
      column_count: 5,
      failure_reason: null,
    });

    fetchPreviewMock.mockResolvedValue({
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
        {
          event_date: "2026-01-03",
          region: "east",
          treated: 1,
          revenue: 90,
        },
      ],
      columns: [
        {
          name: "event_date",
          inferred_type: "date",
          missing_percentage: 0,
          unique_count: 30,
          minimum: "2026-01-01",
          maximum: "2026-01-30",
          mean: null,
          median: null,
        },
        {
          name: "region",
          inferred_type: "string",
          missing_percentage: 0,
          unique_count: 5,
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
      total_rows: 100,
      page: 1,
      page_size: 50,
      total_pages: 2,
      date_range: {
        column: "event_date",
        minimum: "2026-01-01",
        maximum: "2026-01-30",
      },
      treatment_distribution: {},
      outcome_distribution: {},
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

  it("starts the wizard with real dataset columns and detected types", async () => {
    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(
      await screen.findByText("Step 1 of 6"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Time Identification",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Time column"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("option", {
        name: "event_date — date",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("option", {
        name: "region — string",
      }),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("option", {
        name: "fake_column",
      }),
    ).not.toBeInTheDocument();
  });

  it("skips treatment mapping for Marketing Mix Modeling", async () => {
    window.localStorage.setItem(
      "incrementality_dataset_estimator_dataset-1",
      "marketing_mix_model",
    );

    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    expect(await screen.findByText("Step 1 of 5")).toBeInTheDocument();
    expect(
      within(
        screen.getByRole("navigation", { name: "Semantic Mapping steps" }),
      ).queryByText("Treatment"),
    ).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Time column"), {
      target: { value: "event_date" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByText("Step 2 of 5")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Unit column"), {
      target: { value: "region" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByText("Step 3 of 5")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Outcome Identification" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Treatment Identification" }),
    ).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Outcome column"), {
      target: { value: "revenue" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByText("Step 4 of 5")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Spend and Covariates" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByText("Step 5 of 5")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Review and Save" }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("list", { name: "Mapping assignments" }))
        .queryByText(/Treatment/),
    ).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("Semantic mapping request"),
    ).not.toHaveTextContent("treatment_column");

    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Step 4 of 5")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Step 3 of 5")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Step 2 of 5")).toBeInTheDocument();
  });

  it("does not advance without a valid time-column selection", async () => {
    render(
      <SemanticMappingClient
        workspaceId="workspace-1"
        projectId="project-1"
        datasetId="dataset-1"
      />,
    );

    await screen.findByText("Step 1 of 6");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(
      "Choose a valid time column before continuing.",
    );

    expect(
      screen.getByText("Step 1 of 6"),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("heading", {
        name: "Unit Identification",
      }),
    ).not.toBeInTheDocument();
  });


  it("moves from Time to Unit and preserves the Time selection when navigating back", async () => {
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

    expect(
      await screen.findByText("Step 2 of 6"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Unit Identification",
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Back",
      }),
    );

    expect(
      screen.getByText("Step 1 of 6"),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Time column"),
    ).toHaveValue("event_date");
  });


  it("uses real dataset columns for Unit and preserves the selection across navigation", async () => {
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

    expect(
      screen.getByLabelText("Unit column"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("option", {
        name: "region — string",
      }),
    ).not.toBeDisabled();

    expect(
      screen.getByRole("option", {
        name: "revenue — float",
      }),
    ).toBeDisabled();

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
        name: "Back",
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByLabelText("Unit column"),
    ).toHaveValue("region");
  });


  it("validates Unit before advancing to Treatment", async () => {
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

    expect(
      screen.getByText("Step 2 of 6"),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(
      "Choose a valid unit column before continuing.",
    );

    expect(
      screen.getByText("Step 2 of 6"),
    ).toBeInTheDocument();

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

    expect(
      await screen.findByText("Step 3 of 6"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Treatment Identification",
      }),
    ).toBeInTheDocument();
  });


  it("uses real dataset columns and backend-supported types for Treatment", async () => {
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

    expect(
      screen.getByLabelText("Treatment column"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("option", {
        name: "treated — integer",
      }),
    ).not.toBeDisabled();

    expect(
      screen.getByRole("option", {
        name: "region — string",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("option", {
        name: "revenue — float",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("option", {
        name: "event_date — date",
      }),
    ).toBeDisabled();

    fireEvent.change(
      screen.getByLabelText("Treatment column"),
      {
        target: {
          value: "treated",
        },
      },
    );

    expect(
      screen.getByLabelText("Treatment column"),
    ).toHaveValue("treated");
  });


  it("uses only observed preview values as optional Treatment and Control suggestions", async () => {
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

    const treatmentValue =
      screen.getByLabelText("Treatment value");
    const controlValue =
      screen.getByLabelText("Control value");

    expect(treatmentValue).toBeInTheDocument();
    expect(controlValue).toBeInTheDocument();

    expect(treatmentValue).toHaveAttribute(
      "list",
      "semantic-treatment-values",
    );

    expect(controlValue).toHaveAttribute(
      "list",
      "semantic-treatment-values",
    );

    const suggestions = Array.from(
      document.querySelectorAll(
        "#semantic-treatment-values option",
      ),
    ).map((option) =>
      option.getAttribute("value"),
    );

    expect(suggestions).toEqual([
      "1",
      "0",
    ]);

    expect(suggestions).not.toContain("Yes");
    expect(suggestions).not.toContain("No");
    expect(suggestions).not.toContain("Treatment");
    expect(suggestions).not.toContain("Control");
  });


  it("validates Treatment configuration before advancing to Outcome", async () => {
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

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(
      "Enter both Treatment and Control values before continuing.",
    );

    expect(
      screen.getByText("Step 3 of 6"),
    ).toBeInTheDocument();

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
          value: " 1 ",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(
      "Treatment and Control values must be different.",
    );

    expect(
      screen.getByText("Step 3 of 6"),
    ).toBeInTheDocument();

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

    expect(
      await screen.findByText("Step 4 of 6"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Outcome Identification",
      }),
    ).toBeInTheDocument();
  });


  it("uses real numeric dataset columns for Outcome and blocks already assigned roles", async () => {
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

    expect(
      screen.getByLabelText("Outcome column"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("option", {
        name: "revenue — float",
      }),
    ).not.toBeDisabled();

    expect(
      screen.getByRole("option", {
        name: "treated — integer",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("option", {
        name: "region — string",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("option", {
        name: "event_date — date",
      }),
    ).toBeDisabled();

    fireEvent.change(
      screen.getByLabelText("Outcome column"),
      {
        target: {
          value: "revenue",
        },
      },
    );

    expect(
      screen.getByLabelText("Outcome column"),
    ).toHaveValue("revenue");
  });


  it("validates Outcome before advancing to Spend and Covariates", async () => {
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

    expect(
      screen.getByText("Step 4 of 6"),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(
      "Choose a valid outcome column before continuing.",
    );

    expect(
      screen.getByText("Step 4 of 6"),
    ).toBeInTheDocument();

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

    expect(
      await screen.findByText("Step 5 of 6"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Spend and Covariates",
      }),
    ).toBeInTheDocument();
  });


  it("uses an optional real numeric Spend column without reusing assigned roles", async () => {
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

    const spendSelect =
      screen.getByLabelText("Spend column");

    expect(
      spendSelect,
    ).toBeInTheDocument();

    expect(
      within(spendSelect).getByRole("option", {
        name: "No spend column",
      }),
    ).not.toBeDisabled();

    expect(
      within(spendSelect).getByRole("option", {
        name: "ad_spend — float",
      }),
    ).not.toBeDisabled();

    expect(
      within(spendSelect).getByRole("option", {
        name: "revenue — float",
      }),
    ).toBeDisabled();

    expect(
      within(spendSelect).getByRole("option", {
        name: "treated — integer",
      }),
    ).toBeDisabled();

    expect(
      within(spendSelect).getByRole("option", {
        name: "region — string",
      }),
    ).toBeDisabled();

    expect(
      within(spendSelect).getByRole("option", {
        name: "event_date — date",
      }),
    ).toBeDisabled();

    fireEvent.change(
      screen.getByLabelText("Spend column"),
      {
        target: {
          value: "ad_spend",
        },
      },
    );

    expect(
      screen.getByLabelText("Spend column"),
    ).toHaveValue("ad_spend");
  });


  it("supports multiple unique Covariates without overlapping assigned semantic roles", async () => {
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

    fireEvent.change(
      screen.getByLabelText("Spend column"),
      {
        target: {
          value: "ad_spend",
        },
      },
    );

    const competitorCovariate =
      screen.getByLabelText(
        "Covariate competitor_index",
      );

    const holidayCovariate =
      screen.getByLabelText(
        "Covariate holiday_flag",
      );

    expect(
      competitorCovariate,
    ).not.toBeDisabled();

    expect(
      holidayCovariate,
    ).not.toBeDisabled();

    expect(
      screen.getByLabelText(
        "Covariate event_date",
      ),
    ).toBeDisabled();

    expect(
      screen.getByLabelText(
        "Covariate region",
      ),
    ).toBeDisabled();

    expect(
      screen.getByLabelText(
        "Covariate treated",
      ),
    ).toBeDisabled();

    expect(
      screen.getByLabelText(
        "Covariate revenue",
      ),
    ).toBeDisabled();

    expect(
      screen.getByLabelText(
        "Covariate ad_spend",
      ),
    ).toBeDisabled();

    fireEvent.click(
      competitorCovariate,
    );

    fireEvent.click(
      holidayCovariate,
    );

    expect(
      competitorCovariate,
    ).toBeChecked();

    expect(
      holidayCovariate,
    ).toBeChecked();
  });


  it("reviews the exact eight-field semantic mapping request before save", async () => {
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

    fireEvent.change(
      screen.getByLabelText("Spend column"),
      {
        target: {
          value: "ad_spend",
        },
      },
    );

    fireEvent.click(
      screen.getByLabelText(
        "Covariate competitor_index",
      ),
    );

    fireEvent.click(
      screen.getByLabelText(
        "Covariate holiday_flag",
      ),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      await screen.findByText("Step 6 of 6"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Review and Save",
      }),
    ).toBeInTheDocument();

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
      spend_column: "ad_spend",
      covariate_columns: [
        "competitor_index",
        "holiday_flag",
      ],
      treatment_value: "1",
      control_value: "0",
    });
  });

});
