"use client";

import { useState } from "react";

import type { DatasetPreview } from "@/lib/data-products/types";

function columnLabel(name: string): string {
  return name
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatValue(
  name: string,
  value: unknown,
  inferredType?: string,
): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (typeof value === "boolean") {
    return value ? "True" : "False";
  }

  const normalizedName = name.toLowerCase();
  const normalizedType = inferredType?.toLowerCase() ?? "";

  const isPercentage =
    normalizedName.includes("rate") ||
    normalizedName.includes("percentage") ||
    normalizedName.includes("percent") ||
    normalizedName.endsWith("_pct");

  const isCurrency = [
    "revenue",
    "spend",
    "cost",
    "price",
    "amount",
    "sales",
    "order_value",
  ].some((token) => normalizedName.includes(token));

  const isNumericType = [
    "integer",
    "float",
    "number",
    "numeric",
    "decimal",
  ].some((type) => normalizedType.includes(type));

  let numericValue: number | null = null;

  if (typeof value === "number" && Number.isFinite(value)) {
    numericValue = value;
  }

  if (
    typeof value === "string" &&
    (isNumericType || isPercentage || isCurrency)
  ) {
    const trimmed = value.trim();

    const numericPattern = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/;

    if (numericPattern.test(trimmed)) {
      const parsed = Number(trimmed);

      if (Number.isFinite(parsed)) {
        numericValue = parsed;
      }
    }
  }

  if (numericValue === null) {
    return String(value);
  }

  if (isPercentage) {
    const percentage =
      Math.abs(numericValue) <= 1 ? numericValue * 100 : numericValue;

    return `${new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 1,
    }).format(percentage)}%`;
  }

  if (isCurrency) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(numericValue);
  }

  if (normalizedType.includes("integer")) {
    return new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 0,
    }).format(numericValue);
  }

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 4,
  }).format(numericValue);
}

function treatmentStatus(
  name: string,
  value: unknown,
): "treated" | "control" | null {
  const treatmentColumns = [
    "treatment_group",
    "assignment_group",
    "experiment_group",
  ];

  if (!treatmentColumns.includes(name.toLowerCase())) {
    return null;
  }

  const normalizedValue = String(value).toLowerCase();

  if (["1", "true", "treated", "treatment"].includes(normalizedValue)) {
    return "treated";
  }

  if (["0", "false", "control"].includes(normalizedValue)) {
    return "control";
  }

  return null;
}

export function RowEvidenceTable({
  data,
  frameTreatmentValues = true,
  exportHref,
  onPreviousPage,
  onNextPage,
}: {
  data: DatasetPreview;
  frameTreatmentValues?: boolean;
  exportHref?: string;
  onPreviousPage?: () => void;
  onNextPage?: () => void;
}) {
  const [hiddenColumns, setHiddenColumns] = useState<string[]>([]);

  const names = Object.keys(data.rows[0] ?? {});

  const columnsByName = new Map(
    data.columns.map((column) => [column.name, column]),
  );

  const renderedNames = names.filter((name) => !hiddenColumns.includes(name));

  const toggleColumn = (name: string) => {
    setHiddenColumns((current) => {
      if (current.includes(name)) {
        return current.filter((column) => column !== name);
      }

      if (renderedNames.length <= 1) {
        return current;
      }

      return [...current, name];
    });
  };

  return (
    <section
      className="panel explorer-table"
      aria-labelledby="explorer-table-heading"
    >
      <div className="explorer-table-heading">
        <div>
          <p className="eyebrow">Row-level evidence</p>

          <h2 id="explorer-table-heading">Inspect filtered rows</h2>

          <p>Verify individual observations behind the profile and charts.</p>
        </div>

        <div className="explorer-table-toolbar" aria-label="Table controls">
          <details className="explorer-columns-menu">
            <summary role="button" aria-label="Columns">
              <span>Columns</span>

              <small>
                {renderedNames.length}/{names.length}
              </small>
            </summary>

            <div
              className="explorer-columns-popover"
              role="group"
              aria-label="Visible table columns"
            >
              <header>
                <strong>Visible columns</strong>

                <small>Choose what appears in the table.</small>
              </header>

              {names.map((name) => {
                const visible = !hiddenColumns.includes(name);

                return (
                  <label key={name}>
                    <input
                      type="checkbox"
                      aria-label={`${columnLabel(name)} column`}
                      checked={visible}
                      disabled={visible && renderedNames.length === 1}
                      onChange={() => toggleColumn(name)}
                    />

                    <span>{columnLabel(name)}</span>
                  </label>
                );
              })}
            </div>
          </details>

          {exportHref ? (
            <a className="explorer-table-download" href={exportHref} download>
              Download CSV
            </a>
          ) : null}

          <div
            className="explorer-table-pagination"
            aria-label="Table pagination"
          >
            <span>
              Page {data.page} of {data.total_pages}
            </span>

            <button
              type="button"
              aria-label="Previous"
              disabled={data.page <= 1 || !onPreviousPage}
              onClick={onPreviousPage}
            >
              ‹
            </button>

            <button
              type="button"
              aria-label="Next"
              disabled={data.page >= data.total_pages || !onNextPage}
              onClick={onNextPage}
            >
              ›
            </button>
          </div>
        </div>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {renderedNames.map((name, index) => {
                const column = columnsByName.get(name);

                return (
                  <th
                    key={name}
                    data-sticky-column={index < 2 ? String(index) : undefined}
                    data-value-kind={
                      ["integer", "float"].includes(column?.inferred_type ?? "")
                        ? "number"
                        : undefined
                    }
                  >
                    {name.replaceAll("_", " ")}
                  </th>
                );
              })}
            </tr>
          </thead>

          <tbody>
            {data.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {renderedNames.map((name, columnIndex) => {
                  const value = row[name];

                  const column = columnsByName.get(name);

                  const status = frameTreatmentValues
                    ? treatmentStatus(name, value)
                    : null;

                  const missing =
                    value === null || value === undefined || value === "";

                  return (
                    <td
                      key={name}
                      data-missing={missing}
                      data-sticky-column={
                        columnIndex < 2 ? String(columnIndex) : undefined
                      }
                      data-value-kind={
                        typeof value === "number" ? "number" : undefined
                      }
                    >
                      {status ? (
                        <span
                          className="explorer-treatment-pill"
                          data-status={status}
                        >
                          {status === "treated" ? "Treated" : "Control"}
                        </span>
                      ) : (
                        formatValue(name, value, column?.inferred_type)
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
