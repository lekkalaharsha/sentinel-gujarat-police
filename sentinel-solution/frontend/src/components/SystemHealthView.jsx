import { useEffect, useState } from "react";
import { api } from "../api";
import { IconCamera, IconAlert, IconPulse } from "../icons";

// Real numbers only — no fabricated GPU/storage gauges, we have no
// telemetry source for those. Combines /health + /cameras/gap-analysis,
// both real endpoints already used elsewhere in the app.
export default function SystemHealthView({ health, gapAnalysis }) {
  const [retention, setRetention] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.retentionPolicy().then(setRetention).catch((err) => setError(err.message));
  }, []);

  const onlinePct = gapAnalysis?.catalogue_size
    ? Math.round(((health?.active_camera_worker_count ?? 0) / gapAnalysis.catalogue_size) * 100)
    : null;

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>System Health</h1>
          <div className="sub">Pipeline and service status — real endpoints, no simulated metrics</div>
        </div>
      </div>

      <div className="grid4">
        <div className="card2 kpi-row2">
          <div className="stat-icon2 i-confirmed"><IconCamera /></div>
          <div><div className="kpi2-val" style={{ color: "var(--confirmed)" }}>{onlinePct != null ? `${onlinePct}%` : "—"}</div><div className="kpi2-lbl">Cameras online</div></div>
        </div>
        <div className="card2 kpi-row2">
          <div className="stat-icon2 i-danger"><IconAlert /></div>
          <div><div className="kpi2-val">{gapAnalysis?.unhealthy?.length ?? "—"}</div><div className="kpi2-lbl">Unhealthy cameras</div></div>
        </div>
        <div className="card2 kpi-row2">
          <div className="stat-icon2 i-accent"><IconPulse /></div>
          <div><div className="kpi2-val">{gapAnalysis?.missing_department?.length ?? "—"}</div><div className="kpi2-lbl">Missing department tag</div></div>
        </div>
        <div className="card2 kpi-row2">
          <div className="stat-icon2 i-predicted"><IconPulse /></div>
          <div><div className="kpi2-val">{gapAnalysis?.missing_gis_coordinates?.length ?? "—"}</div><div className="kpi2-lbl">Missing GIS coordinates</div></div>
        </div>
      </div>

      <div className="cols2">
        <div className="card2">
          <div className="card-h2"><h2>Camera catalogue vs. registry</h2></div>
          <div className="metarow2"><span>Live in catalogue</span><b>{gapAnalysis?.catalogue_size ?? "—"}</b></div>
          <div className="metarow2"><span>Onboarded (Model 1)</span><b>{gapAnalysis?.registered_size ?? "—"}</b></div>
          <div className="metarow2"><span>Live but never onboarded</span><b>{gapAnalysis?.live_not_onboarded?.length ?? "—"}</b></div>
          <div className="metarow2" style={{ borderBottom: "none" }}><span>Onboarded but not currently live</span><b>{gapAnalysis?.onboarded_not_live?.length ?? "—"}</b></div>
        </div>
        <div className="card2">
          <div className="card-h2"><h2>Data retention (DPDP)</h2></div>
          {error && <p style={{ color: "var(--danger)", fontSize: 11 }}>{error}</p>}
          {retention ? (
            <>
              <div className="metarow2"><span>Event retention</span><b>{retention.vehicle_data_retention_days} days</b></div>
              <div className="metarow2"><span>Audit log retention</span><b>{retention.audit_log_retention_days} days</b></div>
              <div style={{ fontSize: 10.5, color: "var(--text-dim)", marginTop: 8 }}>{retention.note}</div>
            </>
          ) : !error && <p style={{ color: "var(--text-dim)", fontSize: 11.5 }}>Loading…</p>}
        </div>
      </div>
    </>
  );
}
