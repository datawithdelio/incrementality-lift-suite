import { describe, expect, it } from "vitest";

import {
  geographyMarkerRadius,
  markerPathOptions,
} from "../src/components/analysis-configuration/analysis-geography-map";

describe("Analysis geography map marker styling", () => {
  it("keeps observation-scaled markers compact", () => {
    expect(geographyMarkerRadius(0)).toBe(7);
    expect(geographyMarkerRadius(30)).toBeGreaterThan(7);
    expect(geographyMarkerRadius(1_000_000)).toBe(11);
  });

  it("uses visually distinct treatments for each selection state", () => {
    const included = markerPathOptions("included");
    const excluded = markerPathOptions("excluded");
    const neutral = markerPathOptions("neutral");

    expect(included.fillColor).toBe("#6246e5");
    expect(included.color).toBe("#ffffff");
    expect(excluded.fillColor).toBe("#fff5f6");
    expect(excluded.color).toBe("#a43d49");
    expect(neutral.fillColor).toBe("#ffffff");
    expect(neutral.color).toBe("#5f6878");
  });
});
