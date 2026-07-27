import {
  ArrowRight,
  ChartBar,
  ChartLineUp,
  CheckCircle,
  FileCsv,
  GlobeHemisphereWest,
  Graph,
  Path,
} from "@phosphor-icons/react";
import Link from "next/link";

import type {
  AnalysisEstimatorType,
} from "@/lib/analysis-configuration/request";

type AnalysisMethodStepProps = {
  datasetName: string;
  semanticMappingVersion: number;
  backHref: string;
  selectedEstimator:
    AnalysisEstimatorType | null;
  onSelectEstimator: (
    estimator: AnalysisEstimatorType,
  ) => void;
  onContinue: () => void;
};

const ESTIMATORS: Array<{
  type: AnalysisEstimatorType;
  name: string;
  description: string;
  requirements: string[];
  icon: typeof ChartLineUp;
}> = [
  {
    type: "difference_in_differences",
    name: "Difference in Differences",
    description:
      "Compare changes over time between treated and control groups to estimate causal impact.",
    requirements: [
      "Treatment and control groups",
      "Pre and post periods",
      "Numeric outcome",
    ],
    icon: ChartLineUp,
  },
  {
    type: "synthetic_control",
    name: "Synthetic Control",
    description:
      "Build a weighted counterfactual for one treated unit.",
    requirements: [
      "One treated unit",
      "Multiple donor units",
      "Stable pre-period",
    ],
    icon: Graph,
  },
  {
    type: "geo_holdout",
    name: "Geo Holdout",
    description:
      "Measure incremental impact across treated and control geographies.",
    requirements: [
      "Treated and holdout geographies",
      "Comparable pre-period",
      "Geographic outcome",
    ],
    icon: GlobeHemisphereWest,
  },
  {
    type: "marketing_mix_model",
    name: "Marketing Mix Modeling",
    description:
      "Estimate modeled media contribution across marketing channels.",
    requirements: [
      "Channel spend history",
      "Continuous time series",
      "Outcome by period",
    ],
    icon: ChartBar,
  },
  {
    type: "off_policy_evaluation",
    name: "Off-policy Evaluation",
    description:
      "Estimate the value of a target policy from observed policy data.",
    requirements: [
      "Logged actions",
      "Behavior propensities",
      "Target policy propensities",
    ],
    icon: Path,
  },
];

export function AnalysisMethodStep({
  datasetName,
  semanticMappingVersion,
  backHref,
  selectedEstimator,
  onSelectEstimator,
  onContinue,
}: AnalysisMethodStepProps) {
  return (
    <main className="analysis-method-shell">
      <header className="analysis-method-hero">
        <p className="analysis-method-hero__eyebrow">
          Analysis setup
        </p>
        <p className="sr-only">
          Analysis configuration is ready to
          begin.
        </p>
        <h1>
          Configure Analysis
        </h1>

        <p>
          We&apos;ll help you choose the causal
          measurement approach that best matches
          your study.
        </p>
      </header>

      <section
        className="analysis-inputs"
        aria-label="Analysis inputs"
      >
        <div className="analysis-input">
          <span className="analysis-input__icon">
            <FileCsv
              size={26}
              weight="duotone"
              aria-hidden="true"
            />
          </span>
          <span>
            <strong>{datasetName}</strong>
            <small>Dataset</small>
          </span>
        </div>

        <div className="analysis-input">
          <span className="analysis-input__icon">
            <Graph
              size={26}
              weight="duotone"
              aria-hidden="true"
            />
          </span>
          <span>
            <strong>
              Mapping v
              {semanticMappingVersion}
            </strong>
            <small>Semantic mapping</small>
          </span>
        </div>

        <div className="analysis-input analysis-input--ready">
          <CheckCircle
            size={22}
            weight="fill"
            aria-hidden="true"
          />
          <span>
            <strong>
              Validated and ready
            </strong>
            <small>
              Dataset and mapping can be used for
              analysis.
            </small>
          </span>
        </div>
      </section>

      <section
        className="analysis-method-picker"
        aria-labelledby="analysis-method-heading"
      >
        <h2 id="analysis-method-heading">
          Choose an analysis method
        </h2>

        <p>
          Review what each method needs, then
          select the approach that matches your
          study design.
        </p>

        <div
          className="analysis-method-grid"
          role="group"
          aria-label="Supported analysis methods"
        >
          {ESTIMATORS.map(
            (estimator) => {
              const Icon = estimator.icon;
              const selected =
                  selectedEstimator
                  === estimator.type
              ;

              return (
                <button
                  key={estimator.type}
                  className="analysis-method-card"
                  type="button"
                  aria-pressed={selected}
                  onClick={() => {
                    onSelectEstimator(
                      estimator.type,
                    );
                  }}
                >
                  <span className="analysis-method-card__topline">
                    <span
                      className="analysis-method-card__radio"
                      aria-hidden="true"
                    >
                      {selected ? (
                        <span />
                      ) : null}
                    </span>
                    <span className="analysis-method-card__badge">
                      {selected
                        ? "Selected"
                        : "Supported"}
                    </span>
                  </span>

                  <span className="analysis-method-card__identity">
                    <span className="analysis-method-card__icon">
                      <Icon
                        size={26}
                        weight="duotone"
                        aria-hidden="true"
                      />
                    </span>
                    <span>
                      <strong>
                        {estimator.name}
                      </strong>
                      <span>
                        {estimator.description}
                      </span>
                    </span>
                  </span>

                  <span className="analysis-method-card__requirements">
                    {estimator.requirements.map(
                      (requirement) => (
                        <span key={requirement}>
                          <CheckCircle
                            size={17}
                            weight="fill"
                            aria-hidden="true"
                          />
                          {requirement}
                        </span>
                      ),
                    )}
                  </span>
                </button>
              );
            },
          )}
        </div>

        <footer className="analysis-method-actions">
          <Link
            className="analysis-method-actions__back"
            href={backHref}
          >
            Back
          </Link>

          <button
            type="button"
            disabled={
              selectedEstimator === null
            }
            onClick={onContinue}
          >
            Continue
            <ArrowRight
              size={20}
              aria-hidden="true"
            />
          </button>
        </footer>
      </section>
    </main>
  );
}
