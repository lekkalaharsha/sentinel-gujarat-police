import { useEffect, useState } from "react";
import { api } from "../api";

// Model 3 (VMS Federation & Middleware Integration) — see
// sentinel-solution/docs/models/model-3-vms-federation/. Renders the real
// GET /federation/correlations report (routes_federation.py) directly.
//
// IMPORTANT: System B ("nyc_open_data") is a real, independent, public
// dataset (NYC Open Data's "Open Parking and Camera Violations"), NOT a
// second Gujarat departmental VMS — see the backend's honesty_note, always
// rendered here, never hidden. Zero real plate overlap between the two
// sources is expected by construction (different countries) — a real,
// working correlation engine can honestly report zero matches.
export default function FederationDashboard({ onOpenPlate }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);

  async function load() {
    try {
      setReport(await api.federationCorrelations());
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function exportPdf() {
    setExporting(true);
    try {
      await api.downloadFederationReportPdf();
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (error) return <p className="gap-analysis__error">{error}</p>;
  if (!report) return <p className="gap-analysis__empty">Loading…</p>;

  return (
    <div className="gap-analysis">
      <h3>Federated correlation</h3>
      <p className="sub">{report.honesty_note}</p>

      <div className="gap-analysis__stats">
        <div><strong>{report.total_federated_events}</strong><span>federated events</span></div>
        <div><strong>{report.sources_present.join(", ") || "—"}</strong><span>sources present</span></div>
        <div><strong>{report.correlated_plate_count}</strong><span>correlated plates</span></div>
      </div>

      <h4>Correlated plates (within {report.correlation_window_s}s)</h4>
      {report.correlations.length === 0 && (
        <p className="gap-analysis__empty">
          No cross-system matches. Sentinel's sandbox and the NYC Open Data source share no
          plates by construction, so a correctly-working correlation engine reports zero
          matches between them.
        </p>
      )}
      {report.correlations.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--text-dim)", fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              <th style={{ padding: "0 10px 8px" }}>Plate</th>
              <th style={{ padding: "0 10px 8px" }}>Sources</th>
              <th style={{ padding: "0 10px 8px" }}>Time gap (s)</th>
              <th style={{ padding: "0 10px 8px" }}>Confidence</th>
              <th style={{ padding: "0 10px 8px" }}>Basis</th>
            </tr>
          </thead>
          <tbody>
            {report.correlations.map((c) => (
              <tr
                key={c.plate}
                style={{ borderBottom: "1px solid var(--border)", cursor: onOpenPlate ? "pointer" : "default" }}
                onClick={() => onOpenPlate?.(c.plate)}
              >
                <td style={{ padding: "10px" }}>{c.plate}</td>
                <td style={{ padding: "10px" }}>{c.sources.join(" + ")}</td>
                <td style={{ padding: "10px" }}>{c.time_gap_s.toFixed(0)}</td>
                <td style={{ padding: "10px" }}>{c.correlation_confidence.toFixed(2)}</td>
                {/* A seeded match must never read as a real cross-agency
                    sighting — see the backend's involves_synthetic_source. */}
                <td style={{ padding: "10px" }}>
                  {c.involves_synthetic_source ? (
                    <span style={{ color: "var(--warn, #d97706)", fontWeight: 600 }}>SYNTHETIC</span>
                  ) : (
                    "real sources"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <button onClick={load} className="gap-analysis__refresh">Refresh</button>
      <button onClick={exportPdf} disabled={exporting} className="gap-analysis__refresh">
        {exporting ? "Exporting…" : "Export PDF"}
      </button>
    </div>
  );
}
