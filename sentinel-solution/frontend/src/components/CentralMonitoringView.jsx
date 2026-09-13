import { useMemo } from "react";
import LiveMapView from "./LiveMapView";
import AlertsPanel from "./AlertsPanel";
import StatusTag from "./StatusTag";

// Model 4's "centralised monitoring" deliverable, built by composing what
// Model 2 already ships — NOT a new video pipeline. A statewide control
// room is the same primitives (live HLS tiles, health state, alerts) at a
// different console, not different code; duplicating the Live Network/
// AlertsPanel here just to relabel them would be exactly the "Model 4
// version of a working screen" the task says not to build.
export default function CentralMonitoringView({ cameras, health }) {
  const unhealthy = useMemo(() => cameras.filter((c) => c.is_healthy === false), [cameras]);

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Central Monitoring</h1>
          <div className="sub">Statewide command-centre view — composed from Model 2's real live-viewing stack</div>
        </div>
      </div>

      <div className="grid4">
        <div className="card2 kpi-row2">
          <div>
            <div className="kpi2-val" style={{ color: "var(--confirmed)" }}>{health?.active_camera_worker_count ?? 0}</div>
            <div className="kpi2-lbl">Feeds online</div>
          </div>
        </div>
        <div className="card2 kpi-row2">
          <div><div className="kpi2-val" style={{ color: "var(--danger)" }}>{unhealthy.length}</div><div className="kpi2-lbl">Unhealthy cameras</div></div>
        </div>
        <div className="card2 kpi-row2">
          <div><div className="kpi2-val">{[...new Set(cameras.map((c) => c.department).filter(Boolean))].length}</div><div className="kpi2-lbl">Departments represented</div></div>
        </div>
        <div className="card2 kpi-row2">
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <StatusTag kind="LIVE" />
            <span style={{ fontSize: 11, color: "var(--text-dim)" }}>4 / 6 tile wall</span>
          </div>
        </div>
      </div>

      <div className="card2">
        <div className="card-h2">
          <h2>Live wall</h2>
          <StatusTag kind="LIVE" />
        </div>
        <p style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 8 }}>
          Multi-camera wall — LIVE. A statewide ~80,000-camera wall showing every feed
          simultaneously is a DESIGN TARGET: no operator console renders that many live
          streams at once — a real deployment routes to it by district/incident, the same
          selective-viewing pattern this pilot's tile cap already demonstrates.
        </p>
        <LiveMapView cameras={cameras} />
      </div>

      <div className="cols2">
        <div className="card2">
          <div className="card-h2">
            <h2>Camera health, by department</h2>
            <StatusTag kind="LIVE" />
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--text-dim)", fontSize: 10.5, textTransform: "uppercase" }}>
                <th style={{ padding: "0 10px 8px" }}>Camera</th>
                <th style={{ padding: "0 10px 8px" }}>Department</th>
                <th style={{ padding: "0 10px 8px" }}>Location</th>
                <th style={{ padding: "0 10px 8px" }}>State</th>
              </tr>
            </thead>
            <tbody>
              {cameras.map((cam) => (
                <tr key={cam.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "8px 10px", fontWeight: 600 }}>{cam.id}</td>
                  <td style={{ padding: "8px 10px" }}>{cam.department || "—"}</td>
                  <td style={{ padding: "8px 10px" }}>{cam.location || "—"}</td>
                  <td style={{ padding: "8px 10px", color: cam.is_healthy ? "var(--confirmed)" : "var(--danger)" }}>
                    {cam.is_healthy ? "Online" : "Offline"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card2">
          <div className="card-h2">
            <h2>Alerts</h2>
            <StatusTag kind="LIVE" />
          </div>
          <AlertsPanel />
        </div>
      </div>
    </>
  );
}
