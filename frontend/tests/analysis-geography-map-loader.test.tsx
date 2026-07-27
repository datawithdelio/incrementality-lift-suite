import { cleanup, render, screen } from "@testing-library/react";

import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/dynamic", () => ({
  default: (
    _loader: unknown,
    options: {
      loading?: () => React.ReactNode;
    },
  ) => {
    return function MockDynamicMap() {
      return options.loading?.() ?? null;
    };
  },
}));

import { AnalysisGeographyMapLoader } from "../src/components/analysis-configuration/analysis-geography-map-loader";

afterEach(() => {
  cleanup();
});

describe("Analysis geography map loader", () => {
  it("provides an SSR-safe loading state", () => {
    render(
      <AnalysisGeographyMapLoader
        geographies={[]}
        selectedGeographies={[]}
        excludedGeographies={[]}
        onInclude={vi.fn()}
        onExclude={vi.fn()}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading interactive map",
    );
  });
});
