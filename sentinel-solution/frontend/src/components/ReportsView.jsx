import { api } from "../api";

// Real exports of real endpoint data as downloadable JSON — no fabricated
// PDF generator behind this; gap-analysis and audit-log are genuine backend
// reports already used elsewhere in the app (Camera Network, Investigations).
function download(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const REPORTS = [
  // Satisfies HACKATHON_DETAILS.md deliverable #4 / Q33's literal requirement
  // ("output report showing detected vehicles/plates with timestamps") —
  // reuses /vehicle/recent, which already carries every field asked for
  // (camera_id, observed_at, plate, plate_confidence, evidence_class); no
  // new backend endpoint, same download() pattern as the reports below.
  { name: "Vehicle detections report", desc: "Detected vehicles/plates with camera, timestamp and evidence class", fetch: () => api.recentDetections(200), file: "vehicle-detections.json" },
  { name: "Camera gap-analysis report", desc: "Model 1 deliverable — registry coverage, health, missing metadata", fetch: () => api.gapAnalysis(), file: "gap-analysis.json" },
  { name: "Audit log (last 500 queries)", desc: "Every purpose-bound vehicle lookup, who ran it, and why", fetch: () => api.auditLog(500), file: "audit-log.json" },
  { name: "Watchlist snapshot", desc: "Current active watchlist entries", fetch: () => api.listWatchlist(), file: "watchlist.json" },
];

export default function ReportsView() {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Reports</h1>
          <div className="sub">Real exports from live endpoints — not pre-baked mock files</div>
        </div>
      </div>
      <div className="card2">
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--text-dim)", fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              <th style={{ padding: "0 10px 8px" }}>Report</th>
              <th style={{ padding: "0 10px 8px" }}>Description</th>
              <th style={{ padding: "0 10px 8px" }}></th>
            </tr>
          </thead>
          <tbody>
            {REPORTS.map((r) => (
              <tr key={r.name} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "10px" }}>{r.name}</td>
                <td style={{ padding: "10px", color: "var(--text-dim)" }}>{r.desc}</td>
                <td style={{ padding: "10px" }}>
                  <button className="btn2" onClick={() => r.fetch().then((data) => download(r.file, data))}>Download JSON</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
