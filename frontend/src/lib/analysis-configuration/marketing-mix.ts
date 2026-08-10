import type { DatasetPreview } from "@/lib/data-products/types";
import type { SemanticMapping } from "@/lib/semantic-mapping/api";

export type MarketingMixConfiguration = {
  mediaChannels: string[];
  controlColumns: string[];
  aggregateSpendColumn: string | null;
  outcomeKind: "revenue" | "conversions" | "outcome";
  saturationHalfSpendDefaults: Record<string, number>;
};

function isNumericColumn(inferredType: string): boolean {
  return inferredType === "integer" || inferredType === "float";
}

function isControlColumn(inferredType: string): boolean {
  return isNumericColumn(inferredType) || inferredType === "boolean";
}

export function deriveMarketingMixConfiguration(
  preview: DatasetPreview,
  mapping: SemanticMapping,
): MarketingMixConfiguration {
const excludedChannels = new Set([
    mapping.time_column,
    mapping.unit_column,
    mapping.outcome_column,
    mapping.treatment_column,
    mapping.spend_column,
    ...mapping.covariate_columns,
  ]);
  const mediaChannels = preview.columns
    .filter(
      (column) =>
        isNumericColumn(column.inferred_type)
        && column.name.endsWith("_spend")
        && !excludedChannels.has(column.name),
    )
    .map((column) => column.name);
  const columnTypes = new Map(
    preview.columns.map((column) => [column.name, column.inferred_type]),
  );

  const controlColumns = mapping.covariate_columns.filter((column) => {
    const inferredType = columnTypes.get(column);
    return inferredType !== undefined && isControlColumn(inferredType);
  });

  const saturationHalfSpendDefaults: Record<string, number> = {};

  for (const channel of mediaChannels) {
    const median = preview.columns.find(
      (column) => column.name === channel,
    )?.median;

    if (
      typeof median === "number" &&
      Number.isFinite(median) &&
      median > 0
    ) {
      saturationHalfSpendDefaults[channel] = median;
    }
  }
  const normalizedOutcome = mapping.outcome_column.toLocaleLowerCase();
  const outcomeKind = normalizedOutcome.includes("conversion")
    ? "conversions"
    : normalizedOutcome.includes("revenue") || normalizedOutcome.includes("sales")
      ? "revenue"
      : "outcome";

  return {
    mediaChannels,
    controlColumns,
    aggregateSpendColumn: mapping.spend_column,
    outcomeKind,
    saturationHalfSpendDefaults,
  };
}
