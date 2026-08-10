import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResultsExperience } from "../src/components/results/results-experience";
import type { AnalysisResultResponse } from "../src/lib/results/types";

const base: AnalysisResultResponse = {
  analysis_run_id: "run-1",
  workspace_id: "workspace-1",
  project_id: "project-1",
  run_status: "succeeded",
  lifecycle_status: "succeeded",
  estimator_type: "difference_in_differences",
  estimator_version: "did-v2",
  analysis_configuration: { intervention_time: "2026-01-01" },
  attempt_count: 1,
  max_attempts: 3,
  failure_information: null,
  result: {
    effect_estimate: 8.2,
    standard_error: 1.9,
    confidence_interval: { low: 4.4, high: 12, confidence_level: 0.95 },
    p_value: 0.004,
    sample_size: 240,
    estimator_version: "did-v2",
    library_name: "statsmodels",
    library_version: "0.14.5",
    technical_diagnostics: {
      design_assessment: "valid",
      causal_claim_allowed: true,
      plain_language_conclusion: "The design supports an estimated causal increase of 8.20.",
      warnings: [],
      sample_counts: { treated_units: 12, control_units: 14 },
      event_study: [{ period: -1, coefficient: 0 }, { period: 1, coefficient: 8.2 }],
      observed_vs_counterfactual: [{ period: 1, observed: 108.2, counterfactual: 100 }],
    },
    business_impact: {
      incremental_outcome: 984,
      relative_lift: 0.082,
      incremental_revenue: 98400,
      incremental_conversions: null,
    },
    created_at: "2026-07-14T20:00:00Z",
  },
};

afterEach(cleanup);

describe("ResultsExperience", () => {
  it("does not report execution as running before status is loaded", () => {
    render(<ResultsExperience state={{ kind: "loading" }} />);

    expect(
      screen.getByText("Loading analysis status"),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("Analysis running"),
    ).not.toBeInTheDocument();
  });

  it("shows an empty state when no result exists", () => {
    render(<ResultsExperience state={{ kind: "missing" }} />);
    expect(screen.getByText("We couldn’t find this analysis")).toBeInTheDocument();
  });

  it("shows queued and retrying states in customer language", () => {
    render(<ResultsExperience state={{ kind: "ready", refreshError: false, data: { ...base, lifecycle_status: "retrying", run_status: "running", result: null } }} />);
    expect(screen.getByText("Retrying analysis")).toBeInTheDocument();
  });

  it("shows honest indeterminate progress while analysis is running", () => {
    render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data: {
            ...base,
            lifecycle_status: "running",
            run_status: "running",
            result: null,
          },
        }}
      />,
    );

    expect(
      screen.getByText(
        "Your analysis is currently being processed.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("progressbar", {
        name: "Analysis running",
      }),
    ).toBeInTheDocument();

    expect(
      screen.queryByText(
        /validating the design/i,
      ),
    ).not.toBeInTheDocument();
  });

  it("shows a refresh warning without replacing the last known running state", () => {
    render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: true,
          data: {
            ...base,
            lifecycle_status: "running",
            run_status: "running",
            result: null,
          },
        }}
      />,
    );

    expect(
      screen.getByText(
        "Analysis running",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(
      "Unable to refresh analysis status",
    );
  });

  it("places the main conclusion before technical detail", () => {
    render(<ResultsExperience state={{ kind: "ready", refreshError: false, data: base }} />);
    expect(screen.getByRole("heading", { name: /estimated causal increase/i })).toBeInTheDocument();
    expect(screen.getByText("+8.2%")).toBeInTheDocument();
    expect(screen.getByText("Technical details")).toBeInTheDocument();
  });

  it("shows warnings without calling an invalid design causal", () => {
    const invalid = structuredClone(base);
    invalid.result!.technical_diagnostics = {
      ...invalid.result!.technical_diagnostics,
      design_assessment: "invalid",
      causal_claim_allowed: false,
      plain_language_conclusion: "The design does not support a causal claim.",
      warnings: ["Pre-treatment trends differ."],
    };
    render(<ResultsExperience state={{ kind: "ready", refreshError: false, data: invalid }} />);
    expect(screen.getByText("Use this result with caution")).toBeInTheDocument();
    expect(screen.getByText("Pre-treatment trends differ.")).toBeInTheDocument();
  });

  it("shows the exact failure reason and a path to fix the analysis", () => {
    render(<ResultsExperience state={{ kind: "ready", refreshError: false, data: { ...base, lifecycle_status: "failed", run_status: "failed", result: null, failure_information: "Difference-in-differences requires treated and control groups." } }} />);
    expect(screen.getByText("This analysis needs attention")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Difference-in-differences requires treated and control groups.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "Fix configuration",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/analyses/new",
    );
  });

  it("shows permission errors without leaking backend text", () => {
    render(<ResultsExperience state={{ kind: "permission" }} />);
    expect(screen.getByText("You don’t have access to this result")).toBeInTheDocument();
  });

  it("renders synthetic-control donor and placebo evidence", () => {
    const synthetic = structuredClone(base);
    synthetic.estimator_type = "synthetic_control";
    synthetic.result!.p_value = 0.111;
    synthetic.result!.confidence_interval = {
      low: 17.1,
      high: 24.8,
      confidence_level: 0.95,
    };
    synthetic.result!.technical_diagnostics = {
      ...synthetic.result!.technical_diagnostics,
      donor_weights: { "donor-a": 0.7, "donor-b": 0.3 },
      pre_treatment_rmspe: 0.8,
      rmspe_ratio: 5.2,
      placebo_p_value: 0.08,
      treatment_effects_over_time: [{ period: "2026-01-01", effect: 8.2 }],
      placebo_tests: [{ unit: "donor-a", rmspe_ratio: 1.1 }],
    };
    render(<ResultsExperience state={{ kind: "ready", refreshError: false, data: synthetic }} />);
    expect(screen.getByText("Synthetic control fit")).toBeInTheDocument();
    expect(screen.getByText("Donor weights")).toBeInTheDocument();
    expect(screen.getByText("Placebo evidence")).toBeInTheDocument();
    expect(
      screen.getByText(/normal-approximation interval.*17.1 to 24.8/i),
    ).toHaveTextContent("In-space placebo inference: p = 0.111");

    const technicalDetails = screen.getByText("Technical details").closest("details");
    expect(technicalDetails).not.toBeNull();
    expect(
      within(technicalDetails as HTMLElement).getByText(
        "Synthetic control with constrained donor weights",
      ),
    ).toBeInTheDocument();
    expect(
      within(technicalDetails as HTMLElement).queryByText(
        "Difference-in-differences",
      ),
    ).not.toBeInTheDocument();
  });

  it("renders geographic assignments independently of fetching", () => {
    const geo = structuredClone(base);
    geo.estimator_type = "geo_holdout";
    geo.result!.technical_diagnostics = {
      ...geo.result!.technical_diagnostics,
      geographic_assignments: [
        { geo: "Boston", latitude: 42.36, longitude: -71.05, assignment: "treatment" },
        { geo: "Atlanta", latitude: 33.75, longitude: -84.39, assignment: "holdout" },
      ],
      balance_diagnostics: { standardized_mean_difference: 0.1 },
      spillover_warnings: [],
    };
    render(<ResultsExperience state={{ kind: "ready", refreshError: false, data: geo }} />);
    expect(screen.getByText("Geographic lift")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Geographic treatment and holdout assignments" })).toBeInTheDocument();
  });

  it("renders MMM posterior contribution and scenario planning", () => {
    const mmm = structuredClone(base);
    mmm.estimator_type = "marketing_mix_model";
    mmm.result!.technical_diagnostics = {
      ...mmm.result!.technical_diagnostics,
      causal_claim_allowed: false,
      plain_language_conclusion: "The posterior is stable enough for channel planning.",
      recommendations_allowed: true,
      channel_contributions: { search: 800, social: 400 },
      posterior_intervals: { search: { low: 500, high: 1000 } },
      channel_roas: { search: 3.2, social: 1.8 },
      budget_response_curves: { search: [{ spend_multiplier: 1, expected_contribution: 800 }] },
      scenario_plan: [{ scenario: "Shift 10%", recommended_channel: "search", budget_to_reallocate: 1000 }],
      convergence: { max_r_hat: 1.01, min_effective_sample_size: 800, divergences: 0 },
    };
    render(<ResultsExperience state={{ kind: "ready", refreshError: false, data: mmm }} />);
    expect(screen.getByText("Channel contribution")).toBeInTheDocument();
    expect(screen.getByText("Budget scenario")).toBeInTheDocument();
    expect(screen.getAllByText("search")).toHaveLength(3);
  });

  it("labels MMM conversion efficiency as conversions per dollar instead of ROAS", () => {
  const mmm = structuredClone(base);

  mmm.estimator_type = "marketing_mix_model";

  mmm.result!.business_impact = {
    incremental_outcome: 120,
    relative_lift: 0.1,
    incremental_revenue: null,
    incremental_conversions: 120,
  };

  mmm.result!.technical_diagnostics = {
    ...mmm.result!.technical_diagnostics,
    causal_claim_allowed: false,
    recommendations_allowed: true,
    channel_contributions: {
      paid_search_spend: 120,
    },
    channel_efficiency: {
      paid_search_spend: 0.0032,
    },
    channel_efficiency_metric:
      "incremental_conversions_per_dollar",
    scenario_plan: [],
    convergence: {
      max_r_hat: 1.01,
      min_effective_sample_size: 800,
      divergences: 0,
    },
  };

  render(
    <ResultsExperience
      state={{
        kind: "ready",
        refreshError: false,
        data: mmm,
      }}
    />,
  );

  expect(
    screen.getByText("Conversions / $ 0.0032"),
  ).toBeInTheDocument();

  expect(
    screen.queryByText(/^ROAS\b/),
  ).not.toBeInTheDocument();

  expect(
    screen.getByText("Across modeled periods"),
  ).toBeInTheDocument();

  expect(
    screen.queryByText("Across treated observations"),
  ).not.toBeInTheDocument();

});



it("renders MMM observed versus fitted outcome diagnostics", () => {
  const mmm = structuredClone(base);

  mmm.estimator_type = "marketing_mix_model";

  mmm.result!.technical_diagnostics = {
    ...mmm.result!.technical_diagnostics,
    channel_contributions: {
      search: 120,
      social: 80,
    },
    posterior_intervals: {
      search: { low: 60, high: 180 },
      social: { low: 30, high: 130 },
    },
    model_fit_series: [
      {
        period: "2026-01-05T00:00:00+00:00",
        observed: 100,
        fitted_mean: 96,
        fitted_low: 90,
        fitted_high: 103,
        residual: 4,
      },
      {
        period: "2026-01-12T00:00:00+00:00",
        observed: 108,
        fitted_mean: 105,
        fitted_low: 98,
        fitted_high: 112,
        residual: 3,
      },
      {
        period: "2026-01-19T00:00:00+00:00",
        observed: 101,
        fitted_mean: 104,
        fitted_low: 97,
        fitted_high: 111,
        residual: -3,
      },
    ],
  };

  render(
    <ResultsExperience
      state={{
        kind: "ready",
        refreshError: false,
        data: mmm,
      }}
    />,
  );

  expect(
    screen.getByRole("heading", {
      name: "Observed vs fitted outcome",
    }),
  ).toBeInTheDocument();

  expect(
    screen.getByRole("img", {
      name: "Observed versus fitted outcome over time",
    }),
  ).toBeInTheDocument();
});

it("renders MMM channel contribution uncertainty as an interval chart", () => {
  const mmm = structuredClone(base);

  mmm.estimator_type = "marketing_mix_model";

  mmm.result!.technical_diagnostics = {
    ...mmm.result!.technical_diagnostics,
    channel_contributions: {
      search: 120,
      social: 80,
    },
    posterior_intervals: {
      search: { low: 60, high: 180 },
      social: { low: 30, high: 130 },
    },
  };

  render(
    <ResultsExperience
      state={{
        kind: "ready",
        refreshError: false,
        data: mmm,
      }}
    />,
  );

  expect(
    screen.getByRole("heading", {
      name: "Channel contribution uncertainty",
    }),
  ).toBeInTheDocument();

  expect(
    screen.getByRole("img", {
      name: "Channel contribution posterior intervals",
    }),
  ).toBeInTheDocument();
});

it("renders MMM residual diagnostics from the persisted fit series", () => {
  const mmm = structuredClone(base);

  mmm.estimator_type = "marketing_mix_model";

  mmm.result!.technical_diagnostics = {
    ...mmm.result!.technical_diagnostics,
    channel_contributions: {
      search: 120,
    },
    posterior_intervals: {
      search: { low: 60, high: 180 },
    },
    model_fit_series: [
      {
        period: "2026-01-05T00:00:00+00:00",
        observed: 100,
        fitted_mean: 96,
        fitted_low: 90,
        fitted_high: 103,
        residual: 4,
      },
      {
        period: "2026-01-12T00:00:00+00:00",
        observed: 108,
        fitted_mean: 105,
        fitted_low: 98,
        fitted_high: 112,
        residual: 3,
      },
      {
        period: "2026-01-19T00:00:00+00:00",
        observed: 101,
        fitted_mean: 104,
        fitted_low: 97,
        fitted_high: 111,
        residual: -3,
      },
    ],
  };

  render(
    <ResultsExperience
      state={{
        kind: "ready",
        refreshError: false,
        data: mmm,
      }}
    />,
  );

  expect(
    screen.getByRole("heading", {
      name: "Residuals over time",
    }),
  ).toBeInTheDocument();

  expect(
    screen.getByRole("img", {
      name: "Model residuals over time",
    }),
  ).toBeInTheDocument();
});

it("renders off-policy comparison and reliability evidence", () => {
    const ope = structuredClone(base);
    ope.estimator_type = "off_policy_evaluation";
    ope.result!.technical_diagnostics = {
      ...ope.result!.technical_diagnostics,
      policy_name: "growth_policy",
      policy_estimates: { importance_sampling: 4.1, self_normalized_importance_sampling: 3.9, doubly_robust: 4.2 },
      effective_sample_size: 180,
      reliability: "strong",
      plain_language_warning: "Historical decisions provide strong overlap.",
      propensity_overlap: { maximum_importance_weight: 2.4 },
    };
    render(<ResultsExperience state={{ kind: "ready", refreshError: false, data: ope }} />);
    expect(screen.getByText("Estimator comparison")).toBeInTheDocument();
    expect(screen.getByText("Effective sample size")).toBeInTheDocument();
    expect(screen.getByText("growth_policy")).toBeInTheDocument();
  });


  it("links completed results to reproducibility lineage", () => {
    render(
      <ResultsExperience
        state={{ kind: "ready", refreshError: false, data: base }}
      />,
    );

    const link = screen.getByRole(
      "link",
      {
        name: "Reproducibility",
      },
    );

    expect(link).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1/lineage",
    );
  });

  it("shows a finalizing state when a succeeded run result is not available yet", () => {
    render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data: {
            ...base,
            run_status: "succeeded",
            lifecycle_status: "succeeded",
            result: null,
          },
        }}
      />,
    );

    expect(
      screen.getByText(
        "Your analysis completed, but the result is still being finalized.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "Return to Status",
      }),
    ).toHaveAttribute(
      "href",
      "/workspaces/workspace-1/projects/project-1/analysis-runs/run-1",
    );
  });


  it("calls retry when a finalized analysis result is not available yet", () => {
    const retry = vi.fn();

    render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data: {
            ...base,
            run_status: "succeeded",
            lifecycle_status: "succeeded",
            result: null,
          },
        }}
        onRetry={retry}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Retry",
      }),
    );

    expect(retry).toHaveBeenCalledTimes(1);
  });


  it("presents off-policy policy value as a probability rather than a treatment effect", () => {
  const ope = structuredClone(base);

  ope.estimator_type = "off_policy_evaluation";
  ope.target_outcome = "conversion";

  ope.result!.business_impact = {
    incremental_outcome: null,
    relative_lift: null,
    incremental_revenue: null,
    incremental_conversions: null,
  };

  ope.result!.effect_estimate = 0.277;
  ope.result!.standard_error = 0.006;
  ope.result!.confidence_interval = {
    low: 0.265,
    high: 0.289,
    confidence_level: 0.95,
  };
  ope.result!.p_value = 0.0001;

  ope.result!.technical_diagnostics = {
    ...ope.result!.technical_diagnostics,
    policy_name: "growth_policy",
    primary_method: "doubly_robust",
    policy_estimates: {
      importance_sampling: 0.278,
      self_normalized_importance_sampling: 0.277,
      doubly_robust: 0.277,
    },
    effective_sample_size: 4929,
    reliability: "strong",
    propensity_overlap: {
      maximum_importance_weight: 1.34,
    },
  };

  render(
    <ResultsExperience
      state={{
        kind: "ready",
        refreshError: false,
        data: ope,
      }}
    />,
  );

  expect(
    screen.getAllByText("Estimated policy value").length,
  ).toBeGreaterThanOrEqual(1);

  expect(
    screen.getAllByText("27.7%").length,
  ).toBeGreaterThanOrEqual(1);

  expect(
    screen.getByText(
      "95% confidence interval 26.5% to 28.9%.",
    ),
  ).toBeInTheDocument();

  expect(
    screen.queryByText("Effect per treated observation"),
  ).not.toBeInTheDocument();

  expect(
    screen.queryByText(/p\s*[<=]/i),
  ).not.toBeInTheDocument();

  expect(
    screen.queryByText("treatment effect"),
  ).not.toBeInTheDocument();

  expect(
    screen.getAllByText("Policy evaluation evidence").length,
  ).toBeGreaterThanOrEqual(1);

  expect(
    screen.queryByText("Causal evidence"),
  ).not.toBeInTheDocument();

  expect(
    screen.getByText("Primary method"),
  ).toBeInTheDocument();

  expect(
    screen.getByText("Doubly robust"),
  ).toBeInTheDocument();

  expect(
    screen.getByText("Estimator used for the reported policy value."),
  ).toBeInTheDocument();

  expect(
    screen.queryByText("Units represented in the design"),
  ).not.toBeInTheDocument();

  expect(
    screen.getByText("Overlap quality"),
  ).toBeInTheDocument();

  expect(
    screen.getByText("Strong"),
  ).toBeInTheDocument();

  expect(
    screen.getByText("Historical policy support is sufficient for estimation."),
  ).toBeInTheDocument();

  expect(
    screen.queryByText("Design quality"),
  ).not.toBeInTheDocument();

  expect(
    screen.queryByText("Treated / control units"),
  ).not.toBeInTheDocument();

  expect(
    screen.getByText("Policy improvement vs behavior policy"),
  ).toBeInTheDocument();

  expect(
    screen.getByText("Not estimated"),
  ).toBeInTheDocument();

  expect(
    screen.getByText("This run estimates the target-policy value only."),
  ).toBeInTheDocument();

  expect(
    screen.getByText("Estimator comparison"),
  ).toBeInTheDocument();

  expect(
    screen.queryByText("Policy comparison"),
  ).not.toBeInTheDocument();

  expect(
    screen.getByText("27.8%"),
  ).toBeInTheDocument();

  expect(
    screen.queryByText("0.278"),
  ).not.toBeInTheDocument();

  expect(
    screen.queryByText("Across treated observations"),
  ).not.toBeInTheDocument();
});


it("does not expose raw result JSON in technical details", () => {
    const { container } = render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data: base,
        }}
      />,
    );

    expect(
      screen.getByText(
        "Technical details",
      ),
    ).toBeInTheDocument();

    expect(
      container.querySelector("pre"),
    ).not.toBeInTheDocument();

    expect(
      screen.queryByText(
        /"analysis_configuration"/,
      ),
    ).not.toBeInTheDocument();
  });


  it("uses average media contribution as the MMM primary result", () => {
    const mmm = structuredClone(base);

    mmm.estimator_type =
      "marketing_mix_model";

    mmm.result!.effect_estimate = 50;

    mmm.result!.business_impact = {
      incremental_outcome: 1200,
      relative_lift: 0.1,
      incremental_revenue: null,
      incremental_conversions: null,
    };

    mmm.result!.technical_diagnostics = {
      ...mmm.result!.technical_diagnostics,
      causal_claim_allowed: false,
      recommendations_allowed: true,
      channel_contributions: {
        search: 800,
        social: 400,
      },
      posterior_intervals: {
        search: {
          low: 500,
          high: 1000,
        },
      },
      convergence: {
        max_r_hat: 1.01,
        min_effective_sample_size: 800,
        divergences: 0,
      },
    };

    const { container } = render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data: mmm,
        }}
      />,
    );

    const heroMetric =
      container.querySelector(
        ".hero-metric",
      );

    expect(heroMetric).toHaveTextContent(
      "50",
    );

    expect(heroMetric).toHaveTextContent(
      "Average media contribution",
    );

    expect(heroMetric).not.toHaveTextContent(
      "estimated lift",
    );
  });


  it("explains when DiD trend-series data is unavailable", () => {
    const historical = structuredClone(base);

    historical.result!.technical_diagnostics = {
      ...historical.result!.technical_diagnostics,
      observed_vs_counterfactual: [],
    };

    render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data: historical,
        }}
      />,
    );

    expect(
      screen.getByText(
        "Trend-series data is not available for this historical result.",
      ),
    ).toBeInTheDocument();
  });


  it("separates the off-policy method assumption from its overlap diagnostics", () => {
    const ope = structuredClone(base);

    ope.estimator_type =
      "off_policy_evaluation";

    ope.result!.business_impact = {
      incremental_outcome: null,
      relative_lift: null,
      incremental_revenue: null,
      incremental_conversions: null,
    };

    ope.result!.technical_diagnostics = {
      ...ope.result!.technical_diagnostics,
      policy_name: "growth_policy",
      primary_method: "doubly_robust",
      policy_estimates: {
        doubly_robust: 4.2,
      },
      effective_sample_size: 180,
      reliability: "strong",
      propensity_overlap: {
        minimum_behavior_propensity: 0.2,
        maximum_importance_weight: 2.4,
      },
    };

    render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data: ope,
        }}
      />,
    );

    expect(
      screen.getByRole(
        "heading",
        {
          name: "Method assumption",
        },
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /adequate support and overlap between the behavior and target policies/i,
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /Effective sample size/i,
      ),
    ).toBeInTheDocument();
  });


  it.each([
    [
      "difference_in_differences",
      /parallel trends/i,
    ],
    [
      "synthetic_control",
      /donor pool can approximate the treated unit/i,
    ],
    [
      "geo_holdout",
      /treated and holdout geographies remain comparable/i,
    ],
    [
      "marketing_mix_model",
      /media effects can be separated from seasonality and other modeled factors/i,
    ],
  ] as const)(
    "shows the methodological assumption for each non-OPE estimator: %s",
    (
      estimatorType,
      expectedAssumption,
    ) => {
      const result = structuredClone(base);

      result.estimator_type =
        estimatorType;

      render(
        <ResultsExperience
          state={{
            kind: "ready",
            refreshError: false,
            data: result,
          }}
        />,
      );

      expect(
        screen.getByRole(
          "heading",
          {
            name: "Method assumption",
          },
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByText(
          expectedAssumption,
        ),
      ).toBeInTheDocument();

      cleanup();
    },
  );


  it("shows the persisted analysis period and completion time in the completed result header", () => {
    const completed = structuredClone(base);

    completed.analysis_configuration = {
      ...completed.analysis_configuration,
      analysis_start_date: "2026-01-01",
      analysis_end_date: "2026-03-31",
    };

    completed.completed_at =
      "2026-04-01T15:30:00Z";

    render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data: completed,
        }}
      />,
    );

    expect(
      screen.getByText(
        /Jan 1, 2026.*Mar 31, 2026/i,
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /Completed Apr 1, 2026/i,
      ),
    ).toBeInTheDocument();
  });


  it("shows the persisted target outcome in the completed result header", () => {
    const completed = {
      ...structuredClone(base),
      target_outcome: "revenue",
    };

    render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data: completed,
        }}
      />,
    );

    expect(
      screen.getByText(
        /Outcome revenue/i,
      ),
    ).toBeInTheDocument();
  });



  it("uses the confidence level returned by the backend", () => {
    const data = {
      ...base,
      result:
        base.result === null
          ? null
          : {
              ...base.result,
              confidence_interval: {
                ...base.result.confidence_interval,
                confidence_level: 0.9,
              },
            },
    };

    render(
      <ResultsExperience
        state={{
          kind: "ready",
          refreshError: false,
          data,
        }}
      />,
    );

    expect(
      screen.getByText(/90% confidence interval/i),
    ).toBeInTheDocument();
  });

});
