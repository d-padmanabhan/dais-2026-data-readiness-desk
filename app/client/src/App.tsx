import type { ReactElement } from "react";
import { useEffect, useRef, useState } from "react";
import * as L from "leaflet";
import "leaflet/dist/leaflet.css";

type QueryResult = {
  columns: { name: string }[];
  rows: string[][];
};

type ApiSummary =
  | {
      status: "ok";
      hmisSummary: QueryResult;
      facilityVerdicts: QueryResult;
      facilityMatches: QueryResult;
    }
  | {
      status: "unavailable";
      message: string;
    };

type FacilityMatch = {
  band: "amber" | "green" | "red";
  binding_reason: string;
  care_substance_missing_count: string;
  data_caution: string;
  has_capability_text: string;
  has_pincode: string;
  has_valid_coordinates: string;
  latitude: string;
  longitude: string;
  name: string;
  numeric_score: string;
  pincode: string;
  source_state_name: string;
  unique_id: string;
};

const FIX_RECOMMENDATIONS = [
  {
    title: "Reconcile facility geography with source coordinates",
    detail:
      "Compare source state, PIN code, latitude, and longitude. Review records where coordinates point to a different state or do not match the stated facility geography.",
    lift: 10,
  },
  {
    title: "Assign district with boundary polygons",
    detail:
      "Use the uploaded district GeoJSON for point-in-polygon assignment, then carry the polygon-derived district into the facility trust verdict.",
    lift: 7,
  },
  {
    title: "Complete missing facility profile fields",
    detail:
      "Fill pincode, capability text, capacity, doctors, and page recency fields before treating facility profiles as planning-ready.",
    lift: 5,
  },
];
const TOP_FIX = FIX_RECOMMENDATIONS[0];

function bandLabel(band: FacilityMatch["band"]): string {
  return band.toUpperCase();
}

function rowsToObjects(result: QueryResult): Record<string, string>[] {
  return result.rows.map((row) =>
    Object.fromEntries(row.map((value, index) => [result.columns[index]?.name ?? `col_${index}`, value])),
  );
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function formatCaution(value?: string): string {
  if (!value) {
    return "No additional caution";
  }
  if (value === "state_grain_hmis_fallback_not_district_reconciliation") {
    return "State-grain fallback; not district-level reconciliation";
  }
  if (value === "state_rollup_before_district_polygon_assignment") {
    return "State rollup before district polygon assignment";
  }
  return value
    .split("_")
    .filter(Boolean)
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(" ");
}

function formatPercent(value?: string): string {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "Unavailable";
  }
  return `${numericValue.toFixed(1)}%`;
}

function displayValue(value?: string): string {
  return value && value !== "null" ? value : "Unavailable";
}

function markerIconForBand(band: FacilityMatch["band"]): L.DivIcon {
  return L.divIcon({
    className: `readiness-map-marker readiness-map-marker-${band}`,
    html: '<span></span>',
    iconAnchor: [12, 12],
    iconSize: [24, 24],
  });
}

function toFacilityRows(result: QueryResult): FacilityMatch[] {
  return rowsToObjects(result).map((row) => ({
    band: row.band === "green" || row.band === "amber" || row.band === "red" ? row.band : "red",
    binding_reason: row.binding_reason ?? "Location: facility has not been assigned to a trusted geography yet",
    care_substance_missing_count: row.care_substance_missing_count ?? "0",
    data_caution: row.data_caution ?? "state_rollup_before_district_polygon_assignment",
    has_capability_text: row.has_capability_text ?? "false",
    has_pincode: row.has_pincode ?? "false",
    has_valid_coordinates: row.has_valid_coordinates ?? "false",
    latitude: row.latitude ?? "",
    longitude: row.longitude ?? "",
    name: row.name ?? "Unnamed facility",
    numeric_score: row.numeric_score ?? "0",
    pincode: row.pincode ?? "",
    source_state_name: row.source_state_name ?? "Unknown",
    unique_id: row.unique_id ?? `${row.name}-${row.source_state_name}`,
  }));
}

export function App(): ReactElement {
  const [summary, setSummary] = useState<ApiSummary | null>(null);
  const [query, setQuery] = useState("aravind eye hospital");
  const [lens, setLens] = useState<"Facility" | "Location">("Facility");
  const [selectedFacilityId, setSelectedFacilityId] = useState("");
  const [simulated, setSimulated] = useState(false);
  const mapElementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/readiness-summary", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`API request failed: HTTP ${response.status}`);
        }
        return response.json() as Promise<ApiSummary>;
      })
      .then(setSummary)
      .catch((error: unknown) => {
        if (error instanceof Error && error.name !== "AbortError") {
          setSummary({ status: "unavailable", message: error.message });
        }
      });
    return () => controller.abort();
  }, []);

  const hmisRows = summary?.status === "ok" ? rowsToObjects(summary.hmisSummary) : [];
  const facilityRows = summary?.status === "ok" ? rowsToObjects(summary.facilityVerdicts) : [];
  const facilities = summary?.status === "ok" ? toFacilityRows(summary.facilityMatches) : [];
  const normalizedQuery = query.trim().toLowerCase();
  const matchingFacilities = facilities.filter((facility) => {
      if (!normalizedQuery) {
        return true;
      }
      return [facility.name, facility.source_state_name, facility.pincode].some((value) =>
        value.toLowerCase().includes(normalizedQuery),
      );
    });
  const filteredFacilities = matchingFacilities.slice(0, 1000);
  const selectedFacility =
    facilities.find((facility) => facility.unique_id === selectedFacilityId) ?? filteredFacilities[0] ?? facilities[0];
  const baseScore = selectedFacility ? Math.round(Number(selectedFacility.numeric_score) * 100) : 0;
  const displayedScore = simulated && TOP_FIX ? clamp(baseScore + TOP_FIX.lift, 0, 100) : baseScore;
  const selectedBand = displayedScore >= 85 ? "green" : displayedScore >= 60 ? "amber" : "red";
  const latitude = Number(selectedFacility?.latitude);
  const longitude = Number(selectedFacility?.longitude);
  const hasCoordinates =
    Boolean(selectedFacility?.latitude) &&
    Boolean(selectedFacility?.longitude) &&
    Number.isFinite(latitude) &&
    Number.isFinite(longitude);
  const mapCenter: [number, number] = hasCoordinates ? [latitude, longitude] : [22.8, 79.2];
  const readinessTitle = selectedFacility?.name ?? "Select a facility";

  useEffect(() => {
    if (!hasCoordinates || !mapElementRef.current) {
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
      return undefined;
    }

    if (!mapRef.current) {
      mapRef.current = L.map(mapElementRef.current, {
        attributionControl: true,
        scrollWheelZoom: false,
      });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(mapRef.current);
    }

    mapRef.current.setView(mapCenter, 8);

    if (markerRef.current) {
      markerRef.current.remove();
    }

    const popupContent = document.createElement("div");
    const popupTitle = document.createElement("strong");
    const popupState = document.createElement("div");
    const popupScore = document.createElement("div");
    popupTitle.textContent = selectedFacility?.name ?? "Selected facility";
    popupState.textContent = selectedFacility?.source_state_name ?? "";
    popupScore.textContent = `Readiness: ${displayedScore}%`;
    popupContent.append(popupTitle, popupState, popupScore);

    markerRef.current = L.marker(mapCenter, { icon: markerIconForBand(selectedBand) })
      .addTo(mapRef.current)
      .bindPopup(popupContent);

    return undefined;
  }, [displayedScore, hasCoordinates, mapCenter, selectedBand, selectedFacility?.name, selectedFacility?.source_state_name]);

  useEffect(
    () => () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    },
    [],
  );

  return (
    <main className="shell">
      <section className="hero">
        <div className="brand-block">
          <p className="brand">Data Readiness Desk</p>
          <p className="lede">Decision-grade trust signals for healthcare facility and public-health data.</p>
        </div>
        <label className="question">
          <span>How trustworthy is the data for</span>
          <input
            aria-label="Search for a facility or place"
            onChange={(event) => {
              setQuery(event.target.value);
              setSelectedFacilityId("");
              setSimulated(false);
            }}
            value={query}
          />
        </label>
        <fieldset className="lens-toggle">
          <legend>Choose a lens</legend>
          {(["Location", "Facility"] as const).map((option) => (
            <label key={option}>
              <input
                checked={lens === option}
                name="lens"
                onChange={() => setLens(option)}
                type="radio"
                value={option}
              />
              {option}
            </label>
          ))}
        </fieldset>
      </section>

      <section className="workspace">
        <article className="score-panel">
          <p className="eyebrow">Readiness Score</p>
          <p className={`score score-${selectedBand}`}>{displayedScore}%</p>
          {simulated ? <p className="delta">+{displayedScore - baseScore} points after simulated fix</p> : null}
          <h2>{readinessTitle}</h2>
          <p className="reason">
            {selectedFacility?.binding_reason ??
              "State-grain health data is available, but facility-level reconciliation is still incomplete."}
          </p>
          <dl className="signal-list">
            <div>
              <dt>PIN code</dt>
              <dd>{selectedFacility?.pincode || "Missing"}</dd>
            </div>
            <div>
              <dt>Capability text</dt>
              <dd>{selectedFacility?.has_capability_text === "true" ? "Present" : "Missing"}</dd>
            </div>
            <div>
              <dt>Pending issue</dt>
              <dd>{formatCaution(selectedFacility?.data_caution)}</dd>
            </div>
          </dl>
          <div className="map-panel" aria-label="Facility map">
            {hasCoordinates ? (
              <div className="leaflet-container" ref={mapElementRef} />
            ) : (
              <div className="map-fallback">
                <p className="eyebrow">Map unavailable</p>
                <p>Coordinates are missing for this facility. Add latitude and longitude before using location trust.</p>
              </div>
            )}
            {hasCoordinates ? (
              <div className="map-caption">
                {selectedFacility?.source_state_name ?? "Unknown"} ({latitude.toFixed(2)}, {longitude.toFixed(2)})
              </div>
            ) : null}
          </div>
        </article>

        <section className="side-panel">
          <label className="match-select">
            <span>Select a match</span>
            <select
              onChange={(event) => {
                setSelectedFacilityId(event.target.value);
                setSimulated(false);
              }}
              value={selectedFacility?.unique_id ?? ""}
            >
              {filteredFacilities.length > 0 ? (
                filteredFacilities.map((facility) => (
                  <option key={facility.unique_id} value={facility.unique_id}>
                    {facility.name} - {facility.source_state_name}
                  </option>
                ))
              ) : (
                <option value="">No facility match found</option>
              )}
            </select>
            <span className="match-help">
              {normalizedQuery ? (
                <>
                  {matchingFacilities.length} matches for "{query}".{" "}
                  <button
                    className="inline-action"
                    onClick={() => {
                      setQuery("");
                      setSelectedFacilityId("");
                      setSimulated(false);
                    }}
                    type="button"
                  >
                    Browse all {facilities.length} facilities
                  </button>
                </>
              ) : (
                <>Showing {filteredFacilities.length} of {facilities.length} loaded facilities.</>
              )}
            </span>
          </label>

          <article className="card fix-card">
            <h2>What will improve data readiness?</h2>
            {FIX_RECOMMENDATIONS.map((fix, index) => (
              <details key={fix.title} open={index === 0}>
                <summary>
                  #{index + 1} {fix.title}
                </summary>
                <p>{fix.detail}</p>
                <p className="fix-lift">Estimated lift: +{fix.lift} points</p>
              </details>
            ))}
            <button onClick={() => setSimulated((current) => !current)} type="button">
              {simulated ? "Reset simulation" : "Simulate applying the top fix"}
            </button>
          </article>
        </section>
      </section>

      <section className="data-section">
        <article className="card evidence-card">
          <h2>Cached HMIS State Summary</h2>
          {summary?.status === "unavailable" ? <p>{summary.message}</p> : null}
          {hmisRows.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>State</th>
                  <th>ANC 4+</th>
                  <th>Institutional Delivery Proxy</th>
                  <th>Caution</th>
                </tr>
              </thead>
              <tbody>
                {hmisRows.map((row) => (
                  <tr key={row.state_name}>
                    <td>{row.state_name}</td>
                    <td>{formatPercent(row.anc_four_plus_rate_percent)}</td>
                    <td>{formatPercent(row.institutional_delivery_to_live_birth_ratio_percent)}</td>
                    <td>{formatCaution(row.data_caution)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Waiting for cached gold output.</p>
          )}
        </article>

        <article className="card evidence-card">
          <h2>Lowest Facility Trust Scores</h2>
          {facilityRows.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>State</th>
                  <th>Facilities</th>
                  <th>Valid Coordinates</th>
                  <th>Band</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {facilityRows.map((row) => (
                  <tr key={row.source_state_name}>
                    <td>{displayValue(row.source_state_name)}</td>
                    <td>{displayValue(row.total_facilities)}</td>
                    <td>
                      {displayValue(row.valid_coordinate_facilities)} / {displayValue(row.total_facilities)}
                    </td>
                    <td>{displayValue(row.band)}</td>
                    <td>{displayValue(row.binding_reason)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Waiting for cached facility verdicts.</p>
          )}
        </article>
      </section>
    </main>
  );
}
