import StatusTag from "./StatusTag";

// Architecture-only screen. Nothing here is deployed: this pilot runs one
// FastAPI process, one SQLite file, one machine — no replication, no
// failover, no second region. Every item on this page carries
// DESIGN TARGET; there is no LIVE/PILOT item to show, and none should be
// invented to make the page look more finished.
const DR_ITEMS = [
  "Redundant API nodes",
  "Replicated database",
  "Object storage replication",
  "Cross-region health monitoring",
  "Automated failover",
  "Backup / restore procedure",
];

export default function ResilienceDRView() {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Resilience &amp; Disaster Recovery</h1>
          <div className="sub">Production architecture — not deployed in the hackathon pilot</div>
        </div>
      </div>

      <div className="card2" style={{ borderColor: "var(--warn)", background: "var(--warn-bg)" }}>
        <p style={{ fontSize: 12.5, margin: 0, fontWeight: 600 }}>
          Production resilience architecture — not deployed in the hackathon pilot.
        </p>
      </div>

      <div className="card2">
        <div className="card-h2">
          <h2>Target topology</h2>
          <StatusTag kind="DESIGN_TARGET" />
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, padding: "8px 0" }}>
          {["Primary Region", "Replicated State", "DR Region"].map((stage, i, arr) => (
            <div key={stage} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{
                border: "1px dashed var(--border-strong)", borderRadius: 8, padding: "10px 18px",
                fontSize: 12.5, fontWeight: 600, color: "var(--text-dim)", minWidth: 220, textAlign: "center",
              }}>
                {stage}
              </div>
              {i < arr.length - 1 && <div style={{ color: "var(--text-dim)", fontSize: 16, lineHeight: 1 }}>↓</div>}
            </div>
          ))}
        </div>
      </div>

      <div className="card2">
        <div className="card-h2">
          <h2>Required capabilities</h2>
          <StatusTag kind="DESIGN_TARGET" />
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <tbody>
            {DR_ITEMS.map((item) => (
              <tr key={item} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "10px", color: "var(--text-dim)" }}>{item}</td>
                <td style={{ padding: "10px", textAlign: "right" }}><StatusTag kind="DESIGN_TARGET" /></td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ fontSize: 10.5, color: "var(--text-dim)", marginTop: 10 }}>
          This pilot has none of the above: a single process, a single SQLite file, no
          second node and no second region.
        </p>
      </div>
    </>
  );
}
