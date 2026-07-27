"use client";

import dynamic from "next/dynamic";

import type { ComponentProps } from "react";

import type { AnalysisGeographyMap } from "./analysis-geography-map";

type AnalysisGeographyMapProps = ComponentProps<typeof AnalysisGeographyMap>;

const DynamicAnalysisGeographyMap = dynamic(
  () =>
    import("./analysis-geography-map").then(
      (module) => module.AnalysisGeographyMap,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="analysis-geography-map__loading" role="status">
        Loading interactive map…
      </div>
    ),
  },
);

export function AnalysisGeographyMapLoader(props: AnalysisGeographyMapProps) {
  return <DynamicAnalysisGeographyMap {...props} />;
}
