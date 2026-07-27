import {
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import {
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  ExplorerVisualizations,
} from "@/components/data-products/explorer-visualizations";

describe("Data Explorer intervention date", () => {
  it("shows and changes the explicit intervention date", () => {
    const onInterventionDateChange = vi.fn();

    render(
      <ExplorerVisualizations
        activeTab="trend"
        onTabChange={vi.fn()}
        columns={[
          {
            name: "conversions",
            inferred_type: "integer",
            missing_percentage: 0,
            unique_count: 10,
            minimum: 90,
            maximum: 120,
            mean: 105,
            median: 105,
          },
        ]}
        selectedOutcome="conversions"
        onOutcomeChange={vi.fn()}
        selectedInterventionDate="2025-07-01"
        onInterventionDateChange={onInterventionDateChange}
        visualizations={{
          time_column: "date",
          treatment_column: "treatment",
          outcome_column: "conversions",
          treatment_start_date: "2025-07-01",
          trend: [
            {
              period: "2025-06-30",
              treatment_value: 100,
              control_value: 90,
              treatment_observations: 1,
              control_observations: 1,
              phase: "pre",
            },
            {
              period: "2025-07-01",
              treatment_value: 120,
              control_value: 92,
              treatment_observations: 1,
              control_observations: 1,
              phase: "post",
            },
          ],
          distribution: {
            minimum: 90,
            maximum: 120,
            mean: 100.5,
            median: 96,
            first_quartile: 91,
            third_quartile: 110,
            outlier_count: 0,
            sample_size: 4,
            bins: [],
          },
          missingness: [],
          balance: null,
          breakdowns: {},
        }}
      />,
    );

    const input = screen.getByLabelText("Intervention date");

    expect(input).toHaveValue("2025-07-01");

    fireEvent.change(input, {
      target: {
        value: "2025-07-08",
      },
    });

    expect(
      onInterventionDateChange,
    ).not.toHaveBeenCalled();

    fireEvent.blur(input);

    expect(
      onInterventionDateChange,
    ).toHaveBeenCalledWith("2025-07-08");
  });
});
