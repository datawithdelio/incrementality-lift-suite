import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalysisPeriodStep } from "@/components/analysis-configuration/analysis-period-step";

afterEach(() => {
  cleanup();
});

describe("premium analysis period experience", () => {
  it("presents the complete causal period as a guided timeline", () => {
    render(
      <AnalysisPeriodStep
        analysisStartDate="2025-01-01"
        interventionDate="2025-07-01"
        analysisEndDate="2025-09-30"
        showInterventionDate
        validationError={null}
        previewError={null}
        previewLoading={false}
        canContinue
        onAnalysisStartDateChange={vi.fn()}
        onInterventionDateChange={vi.fn()}
        onAnalysisEndDateChange={vi.fn()}
        onContinue={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Define analysis period",
      }),
    ).toBeInTheDocument();

    expect(screen.getByRole("note")).toHaveTextContent(
      "The intervention must fall between the start and end dates.",
    );

    expect(screen.getByLabelText("Analysis period timeline")).toHaveTextContent(
      "Jul 1, 2025",
    );

    expect(screen.getByText("Pre-period")).toBeInTheDocument();

    expect(screen.getByText("Post-period")).toBeInTheDocument();
  });

  it("preserves date callbacks and continue behavior", () => {
    const onStartChange = vi.fn();
    const onContinue = vi.fn();

    render(
      <AnalysisPeriodStep
        analysisStartDate=""
        interventionDate=""
        analysisEndDate=""
        showInterventionDate
        validationError={null}
        previewError={null}
        previewLoading={false}
        canContinue
        onAnalysisStartDateChange={onStartChange}
        onInterventionDateChange={vi.fn()}
        onAnalysisEndDateChange={vi.fn()}
        onContinue={onContinue}
      />,
    );

    fireEvent.change(screen.getByLabelText("Analysis start date"), {
      target: {
        value: "2025-01-01",
      },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue",
      }),
    );

    expect(onStartChange).toHaveBeenCalledWith("2025-01-01");

    expect(onContinue).toHaveBeenCalledOnce();
  });

  it("keeps the intervention field absent for non-intervention methods", () => {
    render(
      <AnalysisPeriodStep
        analysisStartDate=""
        interventionDate=""
        analysisEndDate=""
        showInterventionDate={false}
        validationError={null}
        previewError={null}
        previewLoading={false}
        canContinue={false}
        onAnalysisStartDateChange={vi.fn()}
        onInterventionDateChange={vi.fn()}
        onAnalysisEndDateChange={vi.fn()}
        onContinue={vi.fn()}
      />,
    );

    expect(
      screen.queryByLabelText("Intervention date"),
    ).not.toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Continue",
      }),
    ).toBeDisabled();
  });
});
