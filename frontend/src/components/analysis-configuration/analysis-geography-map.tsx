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

export type GeographySelectionState = "included" | "excluded" | "neutral";

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

function selectionStateLabel(state: GeographySelectionState): string {
  return state === "neutral" ? "Unassigned" : state;
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

export function geographyMarkerRadius(observationCount: number): number {
  return Math.min(
    11,
    Math.max(7, 6 + Math.log10(Math.max(0, observationCount) + 1) * 1.5),
  );
}

export function markerPathOptions(state: GeographySelectionState): {
  className: string;
  color: string;
  fillColor: string;
  fillOpacity: number;
  opacity: number;
  weight: number;
} {
  if (state === "included") {
    return {
      className:
        "analysis-geography-marker analysis-geography-marker--included",
      color: "#ffffff",
      fillColor: "#6246e5",
      fillOpacity: 0.96,
      opacity: 1,
      weight: 2.5,
    };
  }

  if (state === "excluded") {
    return {
      className:
        "analysis-geography-marker analysis-geography-marker--excluded",
      color: "#a43d49",
      fillColor: "#fff5f6",
      fillOpacity: 0.98,
      opacity: 1,
      weight: 2.5,
    };
  }

  return {
    className: "analysis-geography-marker analysis-geography-marker--neutral",
    color: "#5f6878",
    fillColor: "#ffffff",
    fillOpacity: 0.96,
    opacity: 0.92,
    weight: 2.25,
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
        states. Marker size reflects observation volume.
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

          const radius = geographyMarkerRadius(geography.observation_count);

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
              <Tooltip
                className="analysis-geography-map__tooltip"
                direction="top"
                offset={[0, -8]}
                opacity={1}
                sticky
              >
                <span className="analysis-geography-map__tooltip-content">
                  <strong>{geography.value}</strong>

                  <span>
                    {geography.observation_count.toLocaleString("en-US")}{" "}
                    observations
                  </span>

                  <small data-state={state}>
                    {selectionStateLabel(state)}
                  </small>
                </span>
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
              aria-label={`Change map selection for ${geography.value}. Current status: ${selectionStateLabel(state)}`}
              data-state={state}
              onClick={() => {
                cycleSelection(geography.value);
              }}
            >
              <span>{geography.value}</span>

              <small>{selectionStateLabel(state)}</small>
            </button>
          );
        })}
      </div>
    </div>
  );
}
