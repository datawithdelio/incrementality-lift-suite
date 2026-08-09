"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useDataQuality } from "../../lib/data-products/use-data-products";
import {
  datasetEstimatorPreferenceKey,
  datasetExplorePath,
  datasetMappingPath,
} from "../../lib/datasets/routes";
import { DataQualityView } from "./data-quality-view";

type DataQualityClientProps = {
  workspaceId: string;
  projectId: string;
  datasetId: string;
};

export function DataQualityClient({
  workspaceId,
  projectId,
  datasetId,
}: DataQualityClientProps) {
  const [estimator, setEstimator] = useState(() =>
    typeof window !== "undefined" &&
    window.localStorage.getItem(datasetEstimatorPreferenceKey(datasetId)) ===
      "marketing_mix_model"
      ? "marketing_mix_model"
      : "difference_in_differences",
  );

  useEffect(() => {
    window.localStorage.setItem(
      datasetEstimatorPreferenceKey(datasetId),
      estimator,
    );
  }, [datasetId, estimator]);

  const { state, dataset } = useDataQuality(
    workspaceId,
    projectId,
    datasetId,
    estimator,
  );

  return (
    <main className="results-shell">
      <nav aria-label="Dataset navigation">
        <Link
          href={datasetExplorePath(
            workspaceId,
            projectId,
            datasetId,
            estimator,
          )}
        >
          Explore Dataset
        </Link>

        <Link
          href={datasetMappingPath(
            workspaceId,
            projectId,
            datasetId,
            estimator,
          )}
        >
          Semantic Mapping
        </Link>
      </nav>

      <div className="filters">
        <label>
          Causal method
          <select
            aria-label="Causal method"
            value={estimator}
            onChange={(event) =>
              setEstimator(event.target.value)
            }
          >
            <option value="difference_in_differences">
              Difference in Differences
            </option>
            <option value="synthetic_control">
              Synthetic Control
            </option>
            <option value="geo_holdout">
              Geo Holdout
            </option>
            <option value="marketing_mix_model">
              Marketing Mix Modeling
            </option>
            <option value="off_policy_evaluation">
              Off-Policy Evaluation
            </option>
          </select>
        </label>
      </div>

      {dataset?.status === "pending_upload" ? (
        <section className="state-card measurement-state">
          <p className="eyebrow">Data Quality</p>
          <h1>Dataset upload is not complete</h1>
          <p>
            Complete the dataset upload before data-quality validation can begin.
          </p>
        </section>
      ) : dataset?.status === "uploaded" ? (
        <section className="state-card measurement-state">
          <p className="eyebrow">Data Quality</p>
          <h1>Validation is pending</h1>
          <p>
            The upload is complete and is waiting for backend validation to begin.
          </p>
        </section>
      ) : dataset?.status === "validating" ? (
        <section className="state-card measurement-state">
          <p className="eyebrow">Data Quality</p>
          <h1>Validation in progress</h1>
          <p>
            Data-quality results will be available when validation finishes.
          </p>
        </section>
      ) : dataset?.status === "failed" ? (
        <section
          className="state-card measurement-state"
          role="alert"
        >
          <p className="eyebrow">Data Quality</p>
          <h1>Dataset validation failed</h1>
          <p>
            {dataset.failure_reason ??
              "The dataset could not be validated."}
          </p>
        </section>
      ) : (
        <DataQualityView state={state} />
      )}
    </main>
  );
}
