import StatusTag from "./StatusTag";

// Every row's status below was derived from the actual code/runtime audit
// this session ran (camera registry, evidence_class.py, federation.py +
// its frozen Model 3 audit, retention config, RBAC/audit routes) — not
// pre-filled from a template. Where a capability sits between two states
// (partial GPS coverage, only 6/12,257 events carrying a plate), both
// labels are shown rather than rounding up to the better-looking one.
const MATRIX = [
  { cap: "Camera Registry", status: ["LIVE"], target: "80k-camera statewide registry" },
  { cap: "GIS", status: ["LIVE", "PILOT"], target: "Statewide PostGIS", note: "22 of 30 pilot cameras have GPS coordinates" },
  { cap: "Live Viewing", status: ["LIVE"], target: "Regional gateways" },
  { cap: "Video Wall", status: ["LIVE"], target: "Multi-centre wall" },
  { cap: "ANPR Events", status: ["LIVE", "PILOT"], target: "Regional GPU workers", note: "6 of 12,257 real events carry a validated plate" },
  { cap: "Vehicle Search", status: ["LIVE"], target: "Distributed search" },
  { cap: "Alerts", status: ["LIVE"], target: "Statewide event bus" },
  { cap: "RBAC", status: ["LIVE"], target: "Enterprise IAM" },
  { cap: "Audit", status: ["LIVE"], target: "Centralized audit" },
  { cap: "Evidence Classification", status: ["LIVE"], target: "§63 evidence-package export (not yet implemented)" },
  { cap: "Retention", status: ["LIVE", "PILOT"], target: "Tiered (hot/warm/cold) storage", note: "single retention window, no tiering" },
  { cap: "Federation (Model 3)", status: ["PILOT"], target: "Real multi-vendor VMS federation", note: "no real second Gujarat departmental VMS exists to federate against — frozen per audit" },
  { cap: "HA / DR", status: ["DESIGN_TARGET"], target: "Multi-region" },
];

export default function StatewideReadinessView() {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Statewide Readiness</h1>
          <div className="sub">Current state vs. production target, capability by capability</div>
        </div>
      </div>

      <div className="card2">
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--text-dim)", fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              <th style={{ padding: "0 10px 10px" }}>Capability</th>
              <th style={{ padding: "0 10px 10px" }}>Current State</th>
              <th style={{ padding: "0 10px 10px" }}>Production Target</th>
            </tr>
          </thead>
          <tbody>
            {MATRIX.map((row) => (
              <tr key={row.cap} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "10px", fontWeight: 600 }}>{row.cap}</td>
                <td style={{ padding: "10px" }}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {row.status.map((s) => <StatusTag key={s} kind={s} />)}
                  </div>
                  {row.note && <div style={{ fontSize: 10.5, color: "var(--text-dim)", marginTop: 4 }}>{row.note}</div>}
                </td>
                <td style={{ padding: "10px", color: "var(--text-dim)" }}>{row.target}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card2">
        <p style={{ fontSize: 11.5, color: "var(--text-dim)", lineHeight: 1.6, margin: 0 }}>
          <strong>How to read this page:</strong> LIVE means backed by a real endpoint you can
          call right now. PILOT means the same code, but validated only at this hackathon's
          ~30-camera scale, not statewide. DESIGN TARGET means an architecture decision
          documented in SCALABILITY.md with no running implementation.
        </p>
      </div>
    </>
  );
}
