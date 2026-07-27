import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RowEvidenceTable } from "../src/components/data-products/row-evidence-table";

describe("row evidence live API values", () => {
  it("formats numeric strings returned by the API", () => {
    const preview = {
      page: 1,
      total_pages: 1,
      columns: [
        {
          name: "date",
          inferred_type: "string",
        },
        {
          name: "geography",
          inferred_type: "string",
        },
        {
          name: "revenue",
          inferred_type: "float",
        },
        {
          name: "conversion_rate",
          inferred_type: "float",
        },
      ],
      rows: [
        {
          date: "2025-01-03",
          geography: "Newark",
          revenue: "22613.63",
          conversion_rate: "0.033585",
        },
      ],
    };

    render(
      <RowEvidenceTable data={preview as never} exportHref="/preview.csv" />,
    );

    expect(screen.getByText("$22,613.63")).toBeInTheDocument();

    expect(screen.getByText("3.4%")).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: /Columns/i,
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "Download CSV",
      }),
    ).toBeInTheDocument();
  });
});
