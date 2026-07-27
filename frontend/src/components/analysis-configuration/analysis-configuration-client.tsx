"use client";

import { AnalysisConfigurationReview } from "./analysis-configuration-review";

import { AnalysisMethodStep } from "./analysis-method-step";

import { AnalysisPeriodStep } from "./analysis-period-step";

import {
  AnalysisFiltersStep,
  type AnalysisFilterRule,
} from "./analysis-filters-step";

import { AnalysisTreatmentControlStep } from "./analysis-treatment-control-step";

import { AnalysisEstimatorSettingsStep } from "./analysis-estimator-settings-step";

import type {
  AnalysisConfigurationDraft,
  FilterOperator,
} from "@/lib/analysis-configuration/request";

import { useEffect, useState } from "react";

import { SESSION_TOKEN_KEY } from "@/lib/auth/api";
import { fetchGeographySummary, fetchPreview } from "@/lib/data-products/api";
import type {
  DatasetPreview,
  GeographySummary,
} from "@/lib/data-products/types";
import { getDataset, type Dataset } from "@/lib/datasets/api";
import { datasetMappingPath } from "@/lib/datasets/routes";
import { getProjectOverview, type ProjectOverview } from "@/lib/projects/api";
import {
  getLatestSemanticMapping,
  type SemanticMapping,
} from "@/lib/semantic-mapping/api";

type AnalysisConfigurationClientProps = {
  workspaceId: string;
  projectId: string;
};

type AnalysisConfigurationState =
  | {
      kind: "loading";
    }
  | {
      kind: "blocked";
      message: string;
    }
  | {
      kind: "ready";
      project: ProjectOverview;
      dataset: Dataset;
      mapping: SemanticMapping;
    }
  | {
      kind: "error";
      message: string;
    };

type EstimatorType =
  | "difference_in_differences"
  | "synthetic_control"
  | "geo_holdout"
  | "marketing_mix_model"
  | "off_policy_evaluation";

type WizardStep =
  | "method"
  | "period"
  | "filters"
  | "treatment_control"
  | "settings"
  | "review";

type OffPolicyMethod =
  | "importance_sampling"
  | "self_normalized_importance_sampling"
  | "doubly_robust";

function requiresInterventionDate(estimator: EstimatorType): boolean {
  return (
    estimator === "difference_in_differences" ||
    estimator === "synthetic_control" ||
    estimator === "geo_holdout"
  );
}

function analysisPeriodValidationError(
  estimator: EstimatorType,
  analysisStartDate: string,
  interventionDate: string,
  analysisEndDate: string,
): string | null {
  if (
    analysisStartDate &&
    analysisEndDate &&
    analysisStartDate > analysisEndDate
  ) {
    return (
      "Analysis start date must be on or before " + "the analysis end date."
    );
  }

  if (
    requiresInterventionDate(estimator) &&
    analysisStartDate &&
    interventionDate &&
    analysisEndDate &&
    !(
      analysisStartDate < interventionDate &&
      interventionDate <= analysisEndDate
    )
  ) {
    return (
      "Intervention date must be after the analysis start date " +
      "and no later than the analysis end date."
    );
  }

  return null;
}

export function AnalysisConfigurationClient({
  workspaceId,
  projectId,
}: AnalysisConfigurationClientProps) {
  const [state, setState] = useState<AnalysisConfigurationState>({
    kind: "loading",
  });

  const [selectedEstimator, setSelectedEstimator] =
    useState<EstimatorType | null>(null);

  const [wizardStep, setWizardStep] = useState<WizardStep>("method");

  const [analysisStartDate, setAnalysisStartDate] = useState("");

  const [interventionDate, setInterventionDate] = useState("");

  const [analysisEndDate, setAnalysisEndDate] = useState("");

  const [preview, setPreview] = useState<DatasetPreview | null>(null);

  const [geographySummary, setGeographySummary] =
    useState<GeographySummary | null>(null);

  const [previewLoading, setPreviewLoading] = useState(false);

  const [previewError, setPreviewError] = useState<string | null>(null);

  const [selectedFilterColumn, setSelectedFilterColumn] = useState("");

  const [selectedFilterOperator, setSelectedFilterOperator] =
    useState<FilterOperator>("equals");

  const [filterValue, setFilterValue] = useState("");

  const [filterRules, setFilterRules] = useState<AnalysisFilterRule[]>([]);

  const [selectedGeographies, setSelectedGeographies] = useState<string[]>([]);

  const [excludedGeographies, setExcludedGeographies] = useState<string[]>([]);

  const [segmentColumn, setSegmentColumn] = useState("");

  const [selectedSegments, setSelectedSegments] = useState<string[]>([]);

  const [excludedSegments, setExcludedSegments] = useState<string[]>([]);

  const [treatedUnit, setTreatedUnit] = useState("");

  const [donorPool, setDonorPool] = useState<string[]>([]);

  const [treatedGeoAssignments, setTreatedGeoAssignments] = useState<string[]>(
    [],
  );

  const [controlGeoAssignments, setControlGeoAssignments] = useState<string[]>(
    [],
  );

  const [geoCoordinates, setGeoCoordinates] = useState<
    Record<
      string,
      {
        latitude: string;
        longitude: string;
        source: "dataset" | "manual";
      }
    >
  >({});

  const [geoOutcomeKind, setGeoOutcomeKind] = useState("outcome");

  const [mmmSeasonalityPeriod, setMmmSeasonalityPeriod] = useState("52");

  const [mmmOutcomeKind, setMmmOutcomeKind] = useState("revenue");

  const [mmmAdstockDecay, setMmmAdstockDecay] = useState<
    Record<string, string>
  >({});

  const [mmmSaturationHalfSpend, setMmmSaturationHalfSpend] = useState<
    Record<string, string>
  >({});

  const [policyName, setPolicyName] = useState("");

  const [behaviorPropensityColumn, setBehaviorPropensityColumn] = useState("");

  const [targetPropensityColumn, setTargetPropensityColumn] = useState("");

  const [rewardColumn, setRewardColumn] = useState("");

  const [expectedRewardColumn, setExpectedRewardColumn] = useState("");

  const [primaryMethod, setPrimaryMethod] =
    useState<OffPolicyMethod>("doubly_robust");

  useEffect(() => {
    let active = true;

    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);

    if (!token) {
      queueMicrotask(() => {
        if (active) {
          setState({
            kind: "error",
            message:
              "Your session is no longer available. Please sign in again.",
          });
        }
      });

      return () => {
        active = false;
      };
    }

    async function load(sessionToken: string): Promise<void> {
      try {
        const project = await getProjectOverview(
          sessionToken,
          workspaceId,
          projectId,
        );

        if (!active) {
          return;
        }

        if (!project.latest_dataset_id) {
          setState({
            kind: "blocked",
            message: "Upload a dataset before configuring an analysis.",
          });
          return;
        }

        const dataset = await getDataset(
          sessionToken,
          workspaceId,
          projectId,
          project.latest_dataset_id,
        );

        if (!active) {
          return;
        }

        if (dataset.status !== "ready") {
          setState({
            kind: "blocked",
            message:
              "Your dataset must finish validation before you can configure an analysis.",
          });
          return;
        }

        const mapping = await getLatestSemanticMapping(
          sessionToken,
          workspaceId,
          projectId,
          dataset.id,
        );

        if (!active) {
          return;
        }

        if (mapping === null) {
          setState({
            kind: "blocked",
            message: "Configure semantic mapping before creating an analysis.",
          });
          return;
        }

        setState({
          kind: "ready",
          project,
          dataset,
          mapping,
        });
      } catch {
        if (!active) {
          return;
        }

        setState({
          kind: "error",
          message:
            "We couldn't load the analysis configuration. Please try again.",
        });
      }
    }

    void load(token);

    return () => {
      active = false;
    };
  }, [workspaceId, projectId]);

  async function continueToFilters(): Promise<void> {
    if (state.kind !== "ready") {
      return;
    }

    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);

    if (!token) {
      setPreviewError(
        "Your session is no longer available. Please sign in again.",
      );
      return;
    }

    setPreviewLoading(true);
    setPreviewError(null);

    const controller = new AbortController();

    try {
      const [loadedPreview, loadedGeographySummary] = await Promise.all([
        fetchPreview(
          workspaceId,
          projectId,
          state.dataset.id,
          {
            page: 1,
            search: "",
            sortColumn: "",
            descending: false,
            filterColumn: "",
            filterValue: "",
          },
          token,
          controller.signal,
        ),
        fetchGeographySummary(
          workspaceId,
          projectId,
          state.dataset.id,
          state.mapping.version,
          token,
          controller.signal,
        ),
      ]);

      setPreview(loadedPreview);

      setGeographySummary(loadedGeographySummary);

      setGeoCoordinates((current) => {
        const verifiedCoordinates = Object.fromEntries(
          loadedGeographySummary.geographies
            .filter(
              (geography) =>
                geography.coordinate_status === "verified" &&
                geography.latitude !== null &&
                geography.longitude !== null,
            )
            .map((geography) => [
              geography.value,
              {
                latitude: String(geography.latitude),
                longitude: String(geography.longitude),
                source: "dataset" as const,
              },
            ]),
        );

        return {
          ...verifiedCoordinates,
          ...current,
        };
      });

      setWizardStep("filters");
    } catch {
      setPreviewError(
        "We couldn't load the dataset population. Please try again.",
      );
    } finally {
      setPreviewLoading(false);
    }
  }

  if (state.kind === "loading") {
    return (
      <main>
        <div role="status">Loading analysis configuration…</div>
      </main>
    );
  }

  if (state.kind === "blocked") {
    return (
      <main>
        <h1>Configure Analysis</h1>
        <p>{state.message}</p>
      </main>
    );
  }

  if (state.kind === "error") {
    return (
      <main>
        <h1>Analysis configuration unavailable</h1>
        <p role="alert">{state.message}</p>
      </main>
    );
  }

  if (
    wizardStep === "review" &&
    preview !== null &&
    selectedEstimator !== null
  ) {
    const treatmentControl: AnalysisConfigurationDraft["treatmentControl"] =
      selectedEstimator === "difference_in_differences"
        ? {
            kind: "mapped_binary",
          }
        : selectedEstimator === "synthetic_control"
          ? {
              kind: "synthetic_control",
              treatedUnit,
              donorPool: [...donorPool],
            }
          : selectedEstimator === "geo_holdout"
            ? {
                kind: "geo_holdout",
                treatedGeographies: [...treatedGeoAssignments],
                controlGeographies: [...controlGeoAssignments],
              }
            : selectedEstimator === "marketing_mix_model"
              ? {
                  kind: "not_applicable",
                }
              : {
                  kind: "off_policy_evaluation",
                  policyName,
                  behaviorPropensityColumn,
                  targetPropensityColumn,
                };

    const mmmChannels = Array.from(
      new Set(
        [state.mapping.spend_column, ...state.mapping.covariate_columns].filter(
          (value): value is string =>
            typeof value === "string" && value.length > 0,
        ),
      ),
    );

    const settings: AnalysisConfigurationDraft["settings"] =
      selectedEstimator === "difference_in_differences"
        ? {
            kind: "difference_in_differences",
          }
        : selectedEstimator === "synthetic_control"
          ? {
              kind: "synthetic_control",
            }
          : selectedEstimator === "geo_holdout"
            ? {
                kind: "geo_holdout",
                outcomeKind: geoOutcomeKind as
                  | "outcome"
                  | "revenue"
                  | "conversions",
                coordinates: Object.fromEntries(
                  Object.entries(geoCoordinates).map(
                    ([geography, coordinate]) => [
                      geography,
                      {
                        latitude: Number(coordinate.latitude),
                        longitude: Number(coordinate.longitude),
                      },
                    ],
                  ),
                ),
              }
            : selectedEstimator === "marketing_mix_model"
              ? {
                  kind: "marketing_mix_model",
                  outcomeKind: mmmOutcomeKind as
                    | "revenue"
                    | "conversions"
                    | "outcome",
                  seasonalityPeriod: Number(mmmSeasonalityPeriod),
                  adstockDecay: Object.fromEntries(
                    mmmChannels.map((channel) => [
                      channel,
                      Number(mmmAdstockDecay[channel] ?? "0.5"),
                    ]),
                  ),
                  saturationHalfSpend: Object.fromEntries(
                    mmmChannels.map((channel) => [
                      channel,
                      Number(mmmSaturationHalfSpend[channel] ?? "1"),
                    ]),
                  ),
                }
              : {
                  kind: "off_policy_evaluation",
                  rewardColumn,
                  expectedRewardColumn,
                  primaryMethod,
                };

    const draft: AnalysisConfigurationDraft = {
      estimatorType: selectedEstimator,

      period: {
        analysisStartDate,
        analysisEndDate,
        interventionDate:
          selectedEstimator === "difference_in_differences" ||
          selectedEstimator === "synthetic_control" ||
          selectedEstimator === "geo_holdout"
            ? interventionDate
            : null,
      },

      selection: {
        rowFilters: filterRules.map((rule) => ({
          column: rule.column,
          operator: rule.operator,
          ...(rule.value === undefined
            ? {}
            : {
                value: rule.value,
              }),
        })),

        selectedGeographies: [...selectedGeographies],

        excludedGeographies: [...excludedGeographies],

        segmentColumn,

        selectedSegments: [...selectedSegments],

        excludedSegments: [...excludedSegments],
      },

      treatmentControl,
      settings,
    };

    return (
      <AnalysisConfigurationReview
        draft={draft}
        workspaceId={workspaceId}
        projectId={projectId}
        datasetId={state.dataset.id}
        semanticMappingVersion={state.mapping.version}
        mappingTreatment={{
          column: state.mapping.treatment_column,
          treatmentValue: state.mapping.treatment_value,
          controlValue: state.mapping.control_value,
        }}
      />
    );
  }

  if (
    wizardStep === "settings" &&
    preview !== null &&
    selectedEstimator !== null
  ) {
    return (
      <AnalysisEstimatorSettingsStep
        preview={preview}
        estimator={selectedEstimator}
        treatedGeoAssignments={treatedGeoAssignments}
        controlGeoAssignments={controlGeoAssignments}
        geoCoordinates={geoCoordinates}
        geoOutcomeKind={geoOutcomeKind}
        spendColumn={state.mapping.spend_column}
        covariateColumns={state.mapping.covariate_columns}
        mmmSeasonalityPeriod={mmmSeasonalityPeriod}
        mmmOutcomeKind={mmmOutcomeKind}
        mmmAdstockDecay={mmmAdstockDecay}
        mmmSaturationHalfSpend={mmmSaturationHalfSpend}
        rewardColumn={rewardColumn}
        expectedRewardColumn={expectedRewardColumn}
        primaryMethod={primaryMethod}
        onGeoOutcomeKindChange={setGeoOutcomeKind}
        onGeoCoordinateChange={(geography, field, value) => {
          setGeoCoordinates((current) => {
            const existing = current[geography] ?? {
              latitude: "",
              longitude: "",
              source: "manual" as const,
            };

            return {
              ...current,

              [geography]: {
                ...existing,
                [field]: value,
                source: "manual",
              },
            };
          });
        }}
        onMmmSeasonalityPeriodChange={setMmmSeasonalityPeriod}
        onMmmOutcomeKindChange={setMmmOutcomeKind}
        onMmmAdstockDecayChange={(channel, value) => {
          setMmmAdstockDecay((current) => ({
            ...current,

            [channel]: value,
          }));
        }}
        onMmmSaturationHalfSpendChange={(channel, value) => {
          setMmmSaturationHalfSpend((current) => ({
            ...current,

            [channel]: value,
          }));
        }}
        onRewardColumnChange={setRewardColumn}
        onExpectedRewardColumnChange={setExpectedRewardColumn}
        onPrimaryMethodChange={setPrimaryMethod}
        onContinue={() => {
          setWizardStep("review");
        }}
      />
    );
  }

  if (
    wizardStep === "treatment_control" &&
    preview !== null &&
    geographySummary !== null &&
    selectedEstimator !== null
  ) {
    return (
      <AnalysisTreatmentControlStep
        preview={preview}
        geographySummary={geographySummary}
        estimator={selectedEstimator}
        unitColumn={state.mapping.unit_column}
        treatmentColumn={state.mapping.treatment_column}
        treatmentValue={state.mapping.treatment_value}
        controlValue={state.mapping.control_value}
        treatedUnit={treatedUnit}
        donorPool={donorPool}
        treatedGeoAssignments={treatedGeoAssignments}
        controlGeoAssignments={controlGeoAssignments}
        policyName={policyName}
        behaviorPropensityColumn={behaviorPropensityColumn}
        targetPropensityColumn={targetPropensityColumn}
        onTreatedUnitChange={(value) => {
          setTreatedUnit(value);

          setDonorPool((current) =>
            current.filter((candidate) => candidate !== value),
          );
        }}
        onDonorChange={(value, checked) => {
          setDonorPool((current) =>
            checked
              ? [...current, value]
              : current.filter((candidate) => candidate !== value),
          );
        }}
        onTreatedGeoChange={(value, checked) => {
          setTreatedGeoAssignments((current) =>
            checked
              ? [...current, value]
              : current.filter((candidate) => candidate !== value),
          );
        }}
        onControlGeoChange={(value, checked) => {
          setControlGeoAssignments((current) =>
            checked
              ? [...current, value]
              : current.filter((candidate) => candidate !== value),
          );
        }}
        onPolicyNameChange={setPolicyName}
        onBehaviorPropensityColumnChange={setBehaviorPropensityColumn}
        onTargetPropensityColumnChange={setTargetPropensityColumn}
        onContinue={() => {
          setWizardStep("settings");
        }}
      />
    );
  }

  if (
    wizardStep === "filters" &&
    preview !== null &&
    geographySummary !== null
  ) {
    return (
      <AnalysisFiltersStep
        preview={preview}
        geographySummary={geographySummary}
        unitColumn={state.mapping.unit_column}
        selectedFilterColumn={selectedFilterColumn}
        selectedFilterOperator={selectedFilterOperator}
        filterValue={filterValue}
        filterRules={filterRules}
        selectedGeographies={selectedGeographies}
        excludedGeographies={excludedGeographies}
        segmentColumn={segmentColumn}
        selectedSegments={selectedSegments}
        excludedSegments={excludedSegments}
        onFilterColumnChange={(columnName, defaultOperator) => {
          setSelectedFilterColumn(columnName);

          setFilterValue("");

          if (defaultOperator !== null) {
            setSelectedFilterOperator(defaultOperator);
          }
        }}
        onFilterOperatorChange={setSelectedFilterOperator}
        onFilterValueChange={setFilterValue}
        onAddFilter={(rule) => {
          setFilterRules((current) => [...current, rule]);

          setSelectedFilterColumn("");

          setSelectedFilterOperator("equals");

          setFilterValue("");
        }}
        onRemoveFilter={(ruleId) => {
          setFilterRules((current) =>
            current.filter((candidate) => candidate.id !== ruleId),
          );
        }}
        onSelectedGeographyChange={(value, checked) => {
          setSelectedGeographies((current) =>
            checked
              ? [...current, value]
              : current.filter((candidate) => candidate !== value),
          );
        }}
        onExcludedGeographyChange={(value, checked) => {
          setExcludedGeographies((current) =>
            checked
              ? [...current, value]
              : current.filter((candidate) => candidate !== value),
          );
        }}
        onSegmentColumnChange={(value) => {
          setSegmentColumn(value);

          setSelectedSegments([]);

          setExcludedSegments([]);
        }}
        onSelectedSegmentChange={(value, checked) => {
          setSelectedSegments((current) =>
            checked
              ? [...current, value]
              : current.filter((candidate) => candidate !== value),
          );
        }}
        onExcludedSegmentChange={(value, checked) => {
          setExcludedSegments((current) =>
            checked
              ? [...current, value]
              : current.filter((candidate) => candidate !== value),
          );
        }}
        onContinue={() => {
          setWizardStep("treatment_control");
        }}
      />
    );
  }

  if (wizardStep === "period" && selectedEstimator !== null) {
    const showInterventionDate = requiresInterventionDate(selectedEstimator);

    const periodValidationError = analysisPeriodValidationError(
      selectedEstimator,
      analysisStartDate,
      interventionDate,
      analysisEndDate,
    );

    const periodComplete =
      analysisStartDate.length > 0 &&
      analysisEndDate.length > 0 &&
      (!showInterventionDate || interventionDate.length > 0);

    const canContinuePeriod = periodComplete && periodValidationError === null;

    return (
      <AnalysisPeriodStep
        analysisStartDate={analysisStartDate}
        interventionDate={interventionDate}
        analysisEndDate={analysisEndDate}
        showInterventionDate={showInterventionDate}
        validationError={periodValidationError}
        previewError={previewError}
        previewLoading={previewLoading}
        canContinue={canContinuePeriod}
        onAnalysisStartDateChange={setAnalysisStartDate}
        onInterventionDateChange={setInterventionDate}
        onAnalysisEndDateChange={setAnalysisEndDate}
        onContinue={() => {
          void continueToFilters();
        }}
      />
    );
  }

  return (
    <AnalysisMethodStep
      datasetName={state.dataset.source_filename}
      semanticMappingVersion={state.mapping.version}
      backHref={datasetMappingPath(workspaceId, projectId, state.dataset.id)}
      selectedEstimator={selectedEstimator}
      onSelectEstimator={setSelectedEstimator}
      onContinue={() => {
        if (selectedEstimator !== null) {
          setWizardStep("period");
        }
      }}
    />
  );
}
