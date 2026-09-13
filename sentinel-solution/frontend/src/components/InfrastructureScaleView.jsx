import StatusTag from "./StatusTag";

// Pure architecture visualization — no runtime data, matches
// SCALABILITY.md exactly (the only source of truth for these numbers).
// The 250x figure below is the corrected value (160,000 Mbps / 640 Mbps);
// an earlier "~1000x"/"three orders of magnitude" claim was wrong and is
// not repeated here.
const PIPELINE = [
  "CCTV / Department VMS",
  "Edge / Regional Processing",
  "Normalized Event Layer",
  "Sentinel State Control Plane",
  "Search / Alerts / Evidence / Audit",
];

const CURRENT_PILOT = [
  "FastAPI",
  "React / Vite",
  "SQLite",
  "RTSP / HLS",
  "Local analytics workers (one process, this machine)",
];

const PRODUCTION_TARGET = [
  "Regional stream managers (per-district edge tier)",
  "PostgreSQL / PostGIS",
  "Event bus (structured events only, not raw video)",
  "Distributed object storage",
  "HA/DR",
  "Horizontal scaling",
];

export default function InfrastructureScaleView() {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Infrastructure &amp; Scale</h1>
          <div className="sub">Pilot architecture vs. the production target — SCALABILITY.md, not a running deployment</div>
        </div>
      </div>

      <div className="card2">
        <div className="card-h2"><h2>Data flow</h2></div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, padding: "8px 0" }}>
          {PIPELINE.map((stage, i) => (
            <div key={stage} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{
                border: "1px solid var(--border-strong)", borderRadius: 8, padding: "10px 18px",
                fontSize: 12.5, fontWeight: 600, background: "var(--bg-sunken)", minWidth: 240, textAlign: "center",
              }}>
                {stage}
              </div>
              {i < PIPELINE.length - 1 && <div style={{ color: "var(--text-dim)", fontSize: 16, lineHeight: 1 }}>↓</div>}
            </div>
          ))}
        </div>
      </div>

      <div className="cols2">
        <div className="card2">
          <div className="card-h2">
            <h2>Current Pilot</h2>
            <StatusTag kind="LIVE" />
          </div>
          <ul style={{ fontSize: 12.5, lineHeight: 1.9, paddingLeft: 18, margin: 0 }}>
            {CURRENT_PILOT.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>

        <div className="card2" style={{ borderColor: "var(--border-strong)" }}>
          <div className="card-h2">
            <h2>Production Target</h2>
            <StatusTag kind="DESIGN_TARGET" />
          </div>
          <ul style={{ fontSize: 12.5, lineHeight: 1.9, paddingLeft: 18, margin: 0, color: "var(--text-dim)" }}>
            {PRODUCTION_TARGET.map((item) => <li key={item}>{item}</li>)}
          </ul>
          <p style={{ fontSize: 10.5, color: "var(--text-dim)", marginTop: 10 }}>
            None of the above is deployed in this pilot. No Kafka, Redis, or Kubernetes
            instance exists in this environment.
          </p>
        </div>
      </div>

      <div className="card2">
        <div className="card-h2">
          <h2>Bandwidth arithmetic</h2>
          <StatusTag kind="DESIGN_TARGET" />
        </div>
        <p style={{ fontSize: 12.5, lineHeight: 1.7 }}>
          80,000 cameras × ~2 Mbps average bitrate ≈ <strong>160 Gbps</strong> sustained
          ingress if raw video were centralised — not credible, and not the plan. Structured
          events instead: 80,000 cameras × ~1 KB/s ≈ 80 MB/s ≈ <strong>640 Mbps</strong>{" "}
          sustained event-plane traffic. That is a <strong>~250×</strong> reduction versus raw
          video (160,000 Mbps ÷ 640 Mbps) — corrected from an earlier ~1000× estimate. These
          are planning-arithmetic figures from SCALABILITY.md, not a measured load test; no
          load test has been run against this pilot.
        </p>
      </div>
    </>
  );
}
