import type { ReactElement } from "react";
import { useEffect, useState } from "react";

type ReadinessSummary = {
  lens: string;
  title: string;
  band: "amber" | "green" | "red";
  score: number;
  reason: string;
  caveats: string[];
  nextSteps: string[];
};

type QueryResult = {
  columns: { name: string }[];
  rows: string[][];
};

type ApiSummary =
  | {
      status: "ok";
      hmisSummary: QueryResult;
      facilityVerdicts: QueryResult;
    }
  | {
      status: "unavailable";
      message: string;
    };

const DEMO_SUMMARY: ReadinessSummary = {
  lens: "Disease / Condition",
  title: "HMIS state-grain fallback",
  band: "amber",
  score: 0.72,
  reason: "Amber - geographic grain is state-level, not district-level.",
  caveats: [
    "HMIS is currently available as a state-grain source.",
    "District-level disease reconciliation still needs NFHS and district-grain HMIS.",
    "The app must read cached gold tables only during the demo.",
  ],
  nextSteps: [
    "Use gold_hmis_state_indicator_summary for a fallback story.",
    "Add district-grain source when available.",
    "Keep uncertainty visible in the verdict card.",
  ],
};

function bandLabel(band: ReadinessSummary["band"]): string {
  return band.toUpperCase();
}

function rowsToObjects(result: QueryResult): Record<string, string>[] {
  return result.rows.map((row) =>
    Object.fromEntries(row.map((value, index) => [result.columns[index]?.name ?? `col_${index}`, value])),
  );
}

export function App(): ReactElement {
  const [summary, setSummary] = useState<ApiSummary | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/readiness-summary", { signal: controller.signal })
      .then((response) => response.json() as Promise<ApiSummary>)
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

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">DAIS 2026 Apps & Agents for Good</p>
        <h1>Data Readiness Desk</h1>
        <p className="lede">Can I trust this data for a place, condition, or facility?</p>
      </section>

      <section className="grid">
        <article className="card verdict-card">
          <p className="eyebrow">{DEMO_SUMMARY.lens}</p>
          <div className={`band band-${DEMO_SUMMARY.band}`}>{bandLabel(DEMO_SUMMARY.band)}</div>
          <h2>{DEMO_SUMMARY.title}</h2>
          <p className="score">{Math.round(DEMO_SUMMARY.score * 100)} / 100</p>
          <p>{DEMO_SUMMARY.reason}</p>
        </article>

        <article className="card">
          <h2>Evidence Caveats</h2>
          <ul>
            {DEMO_SUMMARY.caveats.map((caveat) => (
              <li key={caveat}>{caveat}</li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h2>Next Validation Steps</h2>
          <ul>
            {DEMO_SUMMARY.nextSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
        </article>
      </section>

      <section className="data-section">
        <article className="card">
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
                    <td>{Number(row.anc_four_plus_rate_percent).toFixed(1)}%</td>
                    <td>{Number(row.institutional_delivery_to_live_birth_ratio_percent).toFixed(1)}%</td>
                    <td>{row.data_caution}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Waiting for cached gold output.</p>
          )}
        </article>

        <article className="card">
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
                    <td>{row.source_state_name}</td>
                    <td>{row.total_facilities}</td>
                    <td>{row.valid_coordinate_facilities}</td>
                    <td>{row.band}</td>
                    <td>{row.binding_reason}</td>
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
