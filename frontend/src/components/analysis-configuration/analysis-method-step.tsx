import type {
  AnalysisEstimatorType,
} from "@/lib/analysis-configuration/request";

type AnalysisMethodStepProps = {
  datasetName: string;
  semanticMappingVersion: number;
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
}> = [
  {
    type: "difference_in_differences",
    name: "Difference in Differences",
    description:
      "Compare outcome changes between treated and control groups.",
  },
  {
    type: "synthetic_control",
    name: "Synthetic Control",
    description:
      "Build a weighted counterfactual for one treated unit.",
  },
  {
    type: "geo_holdout",
    name: "Geo Holdout",
    description:
      "Measure incremental impact across treated and control geographies.",
  },
  {
    type: "marketing_mix_model",
    name: "Marketing Mix Modeling",
    description:
      "Estimate modeled media contribution across marketing channels.",
  },
  {
    type: "off_policy_evaluation",
    name: "Off-policy Evaluation",
    description:
      "Estimate the value of a target policy from observed policy data.",
  },
];

export function AnalysisMethodStep({
  datasetName,
  semanticMappingVersion,
  selectedEstimator,
  onSelectEstimator,
  onContinue,
}: AnalysisMethodStepProps) {
  return (
    <main>
      <h1>
        Configure Analysis
      </h1>

      <p>
        Analysis configuration is ready to begin.
      </p>

      <p>
        Dataset: {datasetName}
      </p>

      <p>
        Semantic mapping version{" "}
        {semanticMappingVersion}
      </p>

      <section
        aria-labelledby="analysis-method-heading"
      >
        <h2 id="analysis-method-heading">
          Choose an analysis method
        </h2>

        <p>
          Select the causal measurement method
          that matches your study design.
        </p>

        <div>
          {ESTIMATORS.map(
            (estimator) => (
              <button
                key={estimator.type}
                type="button"
                aria-pressed={
                  selectedEstimator
                  === estimator.type
                }
                onClick={() => {
                  onSelectEstimator(
                    estimator.type,
                  );
                }}
              >
                <strong>
                  {estimator.name}
                </strong>

                <span>
                  {estimator.description}
                </span>
              </button>
            ),
          )}
        </div>

        <button
          type="button"
          disabled={
            selectedEstimator === null
          }
          onClick={onContinue}
        >
          Continue
        </button>
      </section>
    </main>
  );
}
