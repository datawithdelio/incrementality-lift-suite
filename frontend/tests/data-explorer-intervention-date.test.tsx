import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExplorerVisualizations } from "@/components/data-products/explorer-visualizations";

const visualizations = {
  time_column: "date",
  treatment_column: "treatment",
  outcome_column: "conversions",
  treatment_start_date: "2026-05-25",
  trend: [
    {
      period: "2026-01-05",
      treatment_value: 100,
      control_value: 90,
      treatment_observations: 1,
      control_observations: 1,
      phase: "pre" as const,
    },
    {
      period: "2026-07-27",
      treatment_value: 120,
      control_value: 92,
      treatment_observations: 1,
      control_observations: 1,
      phase: "post" as const,
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
};

const columns = [
  {
    name: "conversions",
    inferred_type: "integer" as const,
    missing_percentage: 0,
    unique_count: 10,
    minimum: 90,
    maximum: 120,
    mean: 105,
    median: 105,
  },
];

function ControlledIntervention({
  initialValue,
  onCommit,
}: {
  initialValue: string;
  onCommit: (value: string) => void;
}) {
  const [value, setValue] = useState(initialValue);

  return (
    <ExplorerVisualizations
      activeTab="trend"
      onTabChange={vi.fn()}
      columns={columns}
      selectedOutcome="conversions"
      onOutcomeChange={vi.fn()}
      selectedInterventionDate={value}
      onInterventionDateChange={(nextValue) => {
        onCommit(nextValue);
        setValue(nextValue);
      }}
      visualizations={visualizations}
    />
  );
}

afterEach(() => {
  cleanup();
});

describe("Data Explorer intervention date", () => {
  it("never commits intermediate native year values", () => {
    const onCommit = vi.fn();

    render(
      <ControlledIntervention
        initialValue=""
        onCommit={onCommit}
      />,
    );

    const input = screen.getByLabelText("Intervention date");

    for (const intermediateValue of [
      "0002-05-25",
      "0020-05-25",
      "0202-05-25",
    ]) {
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: intermediateValue } });

      expect(onCommit).not.toHaveBeenCalled();

      fireEvent.blur(input);

      expect(onCommit).not.toHaveBeenCalled();
      expect(input).toHaveValue(intermediateValue);
      expect(
        screen.getByText(
          "Choose a date between Jan 5, 2026 and Jul 27, 2026.",
        ),
      ).toBeInTheDocument();
    }

    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "2026-05-25" } });

    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(onCommit).toHaveBeenCalledWith("2026-05-25");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    fireEvent.blur(input);

    expect(onCommit).toHaveBeenCalledTimes(1);
  });

  it("commits a complete valid date immediately and does not duplicate on blur", () => {
    const onCommit = vi.fn();

    render(
      <ControlledIntervention
        initialValue="2025-07-25"
        onCommit={onCommit}
      />,
    );

    const input = screen.getByLabelText("Intervention date");

    fireEvent.change(input, { target: { value: "2026-05-25" } });

    expect(input).toHaveValue("2026-05-25");
    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(onCommit).toHaveBeenCalledWith("2026-05-25");

    fireEvent.blur(input);

    expect(onCommit).toHaveBeenCalledTimes(1);

    fireEvent.blur(input);

    expect(onCommit).toHaveBeenCalledTimes(1);
  });

  it("commits the live input value on blur when the DOM is ahead of React", () => {
    const onInterventionDateChange = vi.fn();

    render(
      <ExplorerVisualizations
        activeTab="trend"
        onTabChange={vi.fn()}
        columns={columns}
        selectedOutcome="conversions"
        onOutcomeChange={vi.fn()}
        selectedInterventionDate="2025-07-25"
        onInterventionDateChange={onInterventionDateChange}
        visualizations={visualizations}
      />,
    );

    const input = screen.getByLabelText("Intervention date") as HTMLInputElement;
    const nativeValueSetter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    )?.set;

    nativeValueSetter?.call(input, "2026-05-25");
    fireEvent.blur(input);

    expect(onInterventionDateChange).toHaveBeenCalledTimes(1);
    expect(onInterventionDateChange).toHaveBeenCalledWith("2026-05-25");
  });

  it("renders the parent date instead of a stale backend fallback", () => {
    const props = {
      activeTab: "trend" as const,
      onTabChange: vi.fn(),
      columns,
      selectedOutcome: "conversions",
      onOutcomeChange: vi.fn(),
      onInterventionDateChange: vi.fn(),
      visualizations,
    };
    const { rerender } = render(
      <ExplorerVisualizations
        {...props}
        selectedInterventionDate="2025-07-25"
      />,
    );

    rerender(
      <ExplorerVisualizations
        {...props}
        selectedInterventionDate="2026-05-25"
      />,
    );

    expect(screen.getByLabelText("Intervention date")).toHaveValue(
      "2026-05-25",
    );
  });

  it("does not overwrite the native editing buffer during a parent rerender", () => {
    const props = {
      activeTab: "trend" as const,
      onTabChange: vi.fn(),
      columns,
      selectedOutcome: "conversions",
      onOutcomeChange: vi.fn(),
      onInterventionDateChange: vi.fn(),
      visualizations,
    };
    const { rerender } = render(
      <ExplorerVisualizations
        {...props}
        selectedInterventionDate=""
      />,
    );
    const input = screen.getByLabelText("Intervention date");

    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "2026-05-25" } });

    rerender(
      <ExplorerVisualizations
        {...props}
        selectedInterventionDate=""
      />,
    );

    expect(input).toHaveValue("2026-05-25");
  });

  it("keeps an absent explicit date empty instead of inventing a filter", () => {
    const onInterventionDateChange = vi.fn();

    render(
      <ExplorerVisualizations
        activeTab="trend"
        onTabChange={vi.fn()}
        columns={columns}
        selectedOutcome="conversions"
        onOutcomeChange={vi.fn()}
        selectedInterventionDate=""
        onInterventionDateChange={onInterventionDateChange}
        visualizations={visualizations}
      />,
    );

    expect(screen.getByLabelText("Intervention date")).toHaveValue("");
    expect(onInterventionDateChange).not.toHaveBeenCalled();
    expect(
      screen.getByText("Detected from dataset: May 25, 2026"),
    ).toBeInTheDocument();
    expect(screen.getByText("Detected intervention date")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Detected from the treatment transition; not applied as an explicit filter",
      ),
    ).toBeInTheDocument();
  });

  it("commits a detected date only after explicit confirmation", () => {
    const onCommit = vi.fn();

    render(<ControlledIntervention initialValue="" onCommit={onCommit} />);

    expect(screen.getByLabelText("Intervention date")).toHaveValue("");
    expect(onCommit).not.toHaveBeenCalled();

    fireEvent.click(
      screen.getByRole("button", { name: "Use detected date" }),
    );

    expect(onCommit).toHaveBeenCalledOnce();
    expect(onCommit).toHaveBeenCalledWith("2026-05-25");
    expect(screen.getByLabelText("Intervention date")).toHaveValue(
      "2026-05-25",
    );
    expect(screen.getByText("Selected intervention date")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Use detected date" }),
    ).not.toBeInTheDocument();
  });
});
