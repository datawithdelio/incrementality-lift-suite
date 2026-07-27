"use client";

import type { LatLngBoundsExpression } from "leaflet";

import {
  CircleMarker,
  MapContainer,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";

import { useEffect, useMemo, useState } from "react";

export type GeoResultAssignment = {
  geo: string;
  latitude: number;
  longitude: number;
  assignment: "treatment" | "holdout";
};

type GeoResultMapProps = {
  assignments: GeoResultAssignment[];
  effectEstimate: number;
  relativeLift: number | null;
  sampleSize: number;
  prePeriodBalance: number | null;
};

const TREATMENT_COLOR = "#5b3fd9";
const HOLDOUT_COLOR = "#42956e";

function formatNumber(input: number, maximumFractionDigits = 2): string {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits,
  }).format(input);
}

function formatSignedNumber(input: number): string {
  const formatted = formatNumber(input, 2);

  return input > 0 ? `+${formatted}` : formatted;
}

function formatLift(input: number | null): string {
  if (input === null || !Number.isFinite(input)) {
    return "Not available";
  }

  const percentage = input * 100;
  const formatted = formatNumber(Math.abs(percentage), 1);

  return percentage > 0
    ? `+${formatted}%`
    : percentage < 0
      ? `-${formatted}%`
      : "0%";
}

function FitResultBounds({
  assignments,
}: {
  assignments: GeoResultAssignment[];
}) {
  const map = useMap();

  const bounds = useMemo(
    () =>
      assignments.map(
        ({ latitude, longitude }) => [latitude, longitude] as [number, number],
      ) as LatLngBoundsExpression,
    [assignments],
  );

  useEffect(() => {
    if (assignments.length === 0) {
      map.setView([39.5, -98.35], 4);

      return;
    }

    if (assignments.length === 1) {
      map.setView([assignments[0].latitude, assignments[0].longitude], 6);

      return;
    }

    map.fitBounds(bounds, {
      padding: [34, 34],
      maxZoom: 5,
    });
  }, [assignments, bounds, map]);

  return null;
}

export function GeoResultMap({
  assignments,
  effectEstimate,
  relativeLift,
  sampleSize,
  prePeriodBalance,
}: GeoResultMapProps) {
  const [selectedGeo, setSelectedGeo] = useState<string | null>(
    assignments[0]?.geo ?? null,
  );

  const selectedGeoIsValid =
    selectedGeo !== null && assignments.some(({ geo }) => geo === selectedGeo);

  const effectiveSelectedGeo = selectedGeoIsValid
    ? selectedGeo
    : (assignments[0]?.geo ?? null);

  const selectedAssignment =
    assignments.find(({ geo }) => geo === effectiveSelectedGeo) ?? null;

  return (
    <div className="geo-result-experience">
      <div
        className="geo-result-map-frame"
        role="img"
        aria-label="Geographic treatment and holdout assignments"
      >
        <MapContainer
          className="geo-result-map-canvas"
          center={[39.5, -98.35]}
          zoom={4}
          minZoom={3}
          maxZoom={10}
          scrollWheelZoom
          attributionControl
        >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />

          <FitResultBounds assignments={assignments} />

          {assignments.map((assignment) => {
            const selected = assignment.geo === effectiveSelectedGeo;

            const markerColor =
              assignment.assignment === "treatment"
                ? TREATMENT_COLOR
                : HOLDOUT_COLOR;

            return (
              <CircleMarker
                key={assignment.geo}
                center={[assignment.latitude, assignment.longitude]}
                radius={selected ? 11 : 8}
                pathOptions={{
                  color: "#ffffff",
                  fillColor: markerColor,
                  fillOpacity: 1,
                  opacity: 1,
                  weight: selected ? 4 : 3,
                }}
                eventHandlers={{
                  click: () => {
                    setSelectedGeo(assignment.geo);
                  },
                }}
              >
                <Tooltip direction="top" offset={[0, -8]}>
                  <strong>{assignment.geo}</strong>

                  <br />

                  {assignment.assignment === "treatment"
                    ? "Treatment"
                    : "Holdout"}
                </Tooltip>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>

      <aside className="geo-result-detail" aria-live="polite">
        <p>Selected geography</p>

        {selectedAssignment ? (
          <>
            <div className="geo-result-detail-heading">
              <div>
                <h3>{selectedAssignment.geo}</h3>

                <span
                  className={`geo-result-group ${
                    selectedAssignment.assignment
                  }`}
                >
                  {selectedAssignment.assignment === "treatment"
                    ? "Treatment"
                    : "Holdout"}
                </span>
              </div>

              <span
                className="geo-result-detail-dot"
                data-group={selectedAssignment.assignment}
                aria-hidden="true"
              />
            </div>

            <dl className="geo-result-detail-grid">
              <div>
                <dt>Latitude</dt>

                <dd>{formatNumber(selectedAssignment.latitude, 4)}</dd>
              </div>

              <div>
                <dt>Longitude</dt>

                <dd>{formatNumber(selectedAssignment.longitude, 4)}</dd>
              </div>

              <div>
                <dt>Analysis-wide effect</dt>

                <dd>{formatSignedNumber(effectEstimate)}</dd>
              </div>

              <div>
                <dt>Analysis-wide lift</dt>

                <dd>{formatLift(relativeLift)}</dd>
              </div>

              <div>
                <dt>Total model observations</dt>

                <dd>{formatNumber(sampleSize, 0)}</dd>
              </div>

              <div>
                <dt>Overall pre-period balance</dt>

                <dd>
                  {prePeriodBalance === null
                    ? "Not available"
                    : formatNumber(prePeriodBalance, 2)}
                </dd>
              </div>
            </dl>

            <p className="geo-result-detail-note">
              These metrics describe the complete treatment-versus-holdout
              analysis. A market-specific causal effect was not estimated for{" "}
              <strong>{selectedAssignment.geo}</strong>.
            </p>
          </>
        ) : (
          <p className="geo-result-empty">
            Select a geography to inspect its assignment.
          </p>
        )}
      </aside>

      <div className="geo-result-chips" aria-label="Geography assignments">
        {assignments.map((assignment) => (
          <button
            key={assignment.geo}
            type="button"
            className={
              assignment.geo === effectiveSelectedGeo ? "is-selected" : ""
            }
            data-group={assignment.assignment}
            aria-pressed={assignment.geo === effectiveSelectedGeo}
            onClick={() => {
              setSelectedGeo(assignment.geo);
            }}
          >
            <i aria-hidden="true" />

            <strong>{assignment.geo}</strong>

            <span>
              {assignment.assignment === "treatment" ? "Treatment" : "Holdout"}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
