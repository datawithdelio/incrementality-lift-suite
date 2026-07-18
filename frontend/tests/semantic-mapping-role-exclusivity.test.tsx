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

import { SemanticMappingClient } from "@/components/semantic-mapping/semantic-mapping-client";
import { SESSION_TOKEN_KEY } from "@/lib/auth/api";

const {
  fetchPreviewMock,
  getDatasetMock,
  getLatestSemanticMappingMock,
} = vi.hoisted(() => ({
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
  createSemanticMapping: vi.fn(),
  getLatestSemanticMapping:
    getLatestSemanticMappingMock,
}));

const columns = [
  {
    name: "event_date",
    inferred_type: "date",
    missing_percentage: 0,
    unique_count: 10,
    minimum: null,
    maximum: null,
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
    name: "cohort",
    inferred_type: "string",
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
    unique_count: 10,
    minimum: 1,
    maximum: 100,
    mean: 50,
    median: 50,
  },
  {
    name: "ad_spend",
    inferred_type: "float",
    missing_percentage: 0,
    unique_count: 10,
    minimum: 1,
    maximum: 100,
    mean: 50,
    median: 50,
  },
  {
    name: "competitor_index",
    inferred_type: "float",
    missing_percentage: 0,
    unique_count: 10,
    minimum: 1,
    maximum: 10,
    mean: 5,
    median: 5,
  },
];

function next() {
  fireEvent.click(
    screen.getByRole("button", {
      name: "Next",
    }),
  );
}

function back() {
  fireEvent.click(
    screen.getByRole("button", {
      name: "Back",
    }),
  );
}

async function reachSpendAndCovariates() {
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
  next();

  fireEvent.change(
    screen.getByLabelText("Unit column"),
    {
      target: {
        value: "region",
      },
    },
  );
  next();

  fireEvent.change(
    screen.getByLabelText("Treatment column"),
    {
      target: {
        value: "cohort",
      },
    },
  );

  fireEvent.change(
    screen.getByLabelText("Treatment value"),
    {
      target: {
        value: "treated",
      },
    },
  );

  fireEvent.change(
    screen.getByLabelText("Control value"),
    {
      target: {
        value: "control",
      },
    },
  );
  next();

  fireEvent.change(
    screen.getByLabelText("Outcome column"),
    {
      target: {
        value: "revenue",
      },
    },
  );
  next();
}

function selectCovariate(
  columnName: string,
) {
  const select = screen.getByLabelText(
    "Covariate columns",
  ) as HTMLSelectElement;

  const option = within(select).getByRole(
    "option",
    {
      name: new RegExp(columnName),
    },
  ) as HTMLOptionElement;

  option.selected = true;
  fireEvent.change(select);
}

describe(
  "Semantic Mapping role exclusivity",
  () => {
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
        columns,
        rows: [
          {
            event_date: "2026-01-01",
            region: "north",
            cohort: "treated",
            revenue: 100,
            ad_spend: 20,
            competitor_index: 5,
          },
          {
            event_date: "2026-01-02",
            region: "south",
            cohort: "control",
            revenue: 90,
            ad_spend: 15,
            competitor_index: 4,
          },
        ],
        metadata: {},
        date_range: null,
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

    it("prevents a selected covariate from also being assigned as Spend", async () => {
      await reachSpendAndCovariates();

      selectCovariate(
        "competitor_index",
      );

      const spendSelect =
        screen.getByLabelText(
          "Spend column",
        );

      expect(
        within(spendSelect).getByRole(
          "option",
          {
            name: /competitor_index/,
          },
        ),
      ).toBeDisabled();
    });

    it("prevents a selected covariate from becoming Outcome after navigating backward", async () => {
      await reachSpendAndCovariates();

      selectCovariate(
        "competitor_index",
      );

      back();

      expect(
        screen.getByText("Step 4 of 6"),
      ).toBeInTheDocument();

      const outcomeSelect =
        screen.getByLabelText(
          "Outcome column",
        );

      expect(
        within(outcomeSelect).getByRole(
          "option",
          {
            name: /competitor_index/,
          },
        ),
      ).toBeDisabled();
    });

    it("prevents the Treatment column from becoming Unit after navigating backward", async () => {
      await reachSpendAndCovariates();

      back();
      back();

      expect(
        screen.getByText("Step 3 of 6"),
      ).toBeInTheDocument();

      back();

      expect(
        screen.getByText("Step 2 of 6"),
      ).toBeInTheDocument();

      const unitSelect =
        screen.getByLabelText(
          "Unit column",
        );

      expect(
        within(unitSelect).getByRole(
          "option",
          {
            name: /cohort/,
          },
        ),
      ).toBeDisabled();
    });
  },
);
