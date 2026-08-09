import type { DatasetPreview } from "@/lib/data-products/types";
import type { SemanticMapping } from "@/lib/semantic-mapping/api";

export type MarketingMixConfiguration = {
  mediaChannels: string[];
  controlColumns: string[];
  aggregateSpendColumn: string | null;
  outcomeKind: "revenue" | "conversions" | "outcome";
};

function isNumericColumn(inferredType: string): boolean {
  return inferredType === "integer" || inferredType === "float";
}

export function deriveMarketingMixConfiguration(
  preview: DatasetPreview,
  mapping: SemanticMapping,
): MarketingMixConfiguration {
  const numericColumnNames = new Set(
    preview.columns
      .filter((column) => isNumericColumn(column.inferred_type))
      .map((column) => column.name),
  );
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
  const controlColumns = mapping.covariate_columns.filter((column) =>
    numericColumnNames.has(column),
  );
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
  };
}
