"use client";

import type { GeographySummaryItem } from "@/lib/data-products/types";

import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";

import { useEffect, useMemo } from "react";

import type { LatLngBoundsExpression } from "leaflet";

type GeographySelectionState = "included" | "excluded" | "neutral";

type AnalysisGeographyMapProps = {
  geographies: GeographySummaryItem[];
  selectedGeographies: string[];
  excludedGeographies: string[];

  onInclude: (value: string, checked: boolean) => void;

  onExclude: (value: string, checked: boolean) => void;
};

type VerifiedGeography = GeographySummaryItem & {
  latitude: number;
  longitude: number;
  coordinate_status: "verified";
};

function selectionState(
  geography: string,
  selectedGeographies: string[],
  excludedGeographies: string[],
): GeographySelectionState {
  if (selectedGeographies.includes(geography)) {
    return "included";
  }

  if (excludedGeographies.includes(geography)) {
    return "excluded";
  }

  return "neutral";
}

function FitVerifiedBounds({
  geographies,
}: {
  geographies: VerifiedGeography[];
}) {
  const map = useMap();

  const bounds = useMemo<LatLngBoundsExpression | null>(() => {
    if (geographies.length === 0) {
      return null;
    }

    return geographies.map((geography) => [
      geography.latitude,
      geography.longitude,
    ]);
  }, [geographies]);

  useEffect(() => {
    if (bounds === null) {
      return;
    }

    map.fitBounds(bounds, {
      padding: [36, 36],
      maxZoom: 10,
    });
  }, [bounds, map]);

  return null;
}

function markerPathOptions(state: GeographySelectionState): {
  color: string;
  fillColor: string;
  fillOpacity: number;
  weight: number;
} {
  if (state === "included") {
    return {
      color: "#5936d9",
      fillColor: "#6d4bea",
      fillOpacity: 0.9,
      weight: 3,
    };
  }

  if (state === "excluded") {
    return {
      color: "#a13c46",
      fillColor: "#cc5b66",
      fillOpacity: 0.82,
      weight: 3,
    };
  }

  return {
    color: "#536174",
    fillColor: "#ffffff",
    fillOpacity: 0.94,
    weight: 2,
  };
}

function formatMetric(value: number | null): string {
  if (value === null) {
    return "Unavailable";
  }

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
  }).format(value);
}

export function AnalysisGeographyMap({
  geographies,
  selectedGeographies,
  excludedGeographies,
  onInclude,
  onExclude,
}: AnalysisGeographyMapProps) {
  const verifiedGeographies = useMemo(
    () =>
      geographies.filter(
        (geography): geography is VerifiedGeography =>
          geography.coordinate_status === "verified" &&
          geography.latitude !== null &&
          geography.longitude !== null,
      ),
    [geographies],
  );

  function cycleSelection(geography: string): void {
    const current = selectionState(
      geography,
      selectedGeographies,
      excludedGeographies,
    );

    if (current === "neutral") {
      onInclude(geography, true);
      return;
    }

    if (current === "included") {
      onInclude(geography, false);

      onExclude(geography, true);
      return;
    }

    onExclude(geography, false);
  }

  if (verifiedGeographies.length === 0) {
    return (
      <div className="analysis-geography-map__empty" role="status">
        <strong>No verified coordinates available</strong>

        <p>
          Add coordinates before using the interactive map. Geography cards
          remain available below.
        </p>
      </div>
    );
  }

  const first = verifiedGeographies[0];

  return (
    <div className="analysis-geography-map">
      <div className="analysis-geography-map__header">
        <div>
          <p>Interactive geography map</p>

          <strong>Pan, zoom, inspect, and select</strong>
        </div>

        <div
          className="analysis-geography-map__legend"
          aria-label="Map selection legend"
        >
          <span data-state="included">Included</span>

          <span data-state="excluded">Excluded</span>

          <span data-state="neutral">Unassigned</span>
        </div>
      </div>

      <p className="analysis-geography-map__instructions">
        Select a marker to cycle through included, excluded, and unassigned
        states.
      </p>

      <MapContainer
        className="analysis-geography-map__canvas"
        center={[first.latitude, first.longitude]}
        zoom={6}
        scrollWheelZoom
        attributionControl
      >
        <TileLayer
          attribution={"&copy; OpenStreetMap contributors"}
          url={"https://tile.openstreetmap.org/{z}/{x}/{y}.png"}
          maxZoom={19}
        />

        <FitVerifiedBounds geographies={verifiedGeographies} />

        {verifiedGeographies.map((geography) => {
          const state = selectionState(
            geography.value,
            selectedGeographies,
            excludedGeographies,
          );

          const radius = Math.min(
            19,
            Math.max(8, 7 + Math.log10(geography.observation_count + 1) * 3),
          );

          return (
            <CircleMarker
              key={geography.value}
              center={[geography.latitude, geography.longitude]}
              radius={radius}
              pathOptions={markerPathOptions(state)}
              eventHandlers={{
                click: () => {
                  cycleSelection(geography.value);
                },
              }}
            >
              <Tooltip direction="top" offset={[0, -4]}>
                <strong>{geography.value}</strong>
                <br />
                {geography.observation_count.toLocaleString("en-US")}{" "}
                observations
                <br />
                Status: {state}
              </Tooltip>

              <Popup>
                <div className="analysis-geography-map__popup">
                  <strong>{geography.value}</strong>

                  <span>
                    {geography.observation_count.toLocaleString("en-US")}{" "}
                    observations
                  </span>

                  <span>
                    Outcome: {formatMetric(geography.metrics.outcome_sum)}
                  </span>

                  <span>
                    Spend: {formatMetric(geography.metrics.spend_sum)}
                  </span>

                  <button
                    type="button"
                    onClick={() => {
                      cycleSelection(geography.value);
                    }}
                  >
                    Change selection
                  </button>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>

      <div className="analysis-geography-map__accessible-list">
        {verifiedGeographies.map((geography) => {
          const state = selectionState(
            geography.value,
            selectedGeographies,
            excludedGeographies,
          );

          return (
            <button
              key={geography.value}
              type="button"
              aria-label={`Change map selection for ${geography.value}. Current status: ${state}`}
              data-state={state}
              onClick={() => {
                cycleSelection(geography.value);
              }}
            >
              <span>{geography.value}</span>

              <small>{state}</small>
            </button>
          );
        })}
      </div>
    </div>
  );
}
