import { useEffect, useState } from "react";
import { api } from "../api";
import StatusTag from "./StatusTag";

// Top half is real backend config (GET /admin/retention-policy, same
// endpoint SettingsView already uses) — not re-typed constants. Bottom
// half is the hot/warm/cold design SCALABILITY.md describes; nothing there
// is implemented, and this screen must never imply otherwise.
export default function StorageRetentionView() {
  const [retention, setRetention] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.retentionPolicy().then(setRetention).catch((err) => setError(err.message));
  }, []);

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Storage &amp; Retention</h1>
          <div className="sub">Real pilot retention config vs. the tiered-storage design target</div>
        </div>
      </div>

      <div className="card2">
        <div className="card-h2">
          <h2>Current Pilot</h2>
          <StatusTag kind="LIVE" />
        </div>
        {error && <p style={{ color: "var(--danger)", fontSize: 12 }}>{error}</p>}
        {retention && (
          <>
            <div className="grid4">
              <div className="card2 kpi-row2">
                <div><div className="kpi2-val">{retention.vehicle_data_retention_days}</div><div className="kpi2-lbl">Vehicle/event retention (days)</div></div>
              </div>
              <div className="card2 kpi-row2">
                <div><div className="kpi2-val">{retention.audit_log_retention_days}</div><div className="kpi2-lbl">Audit retention (days)</div></div>
              </div>
              <div className="card2 kpi-row2">
                <div><div className="kpi2-val">{Math.round(retention.sweep_interval_s / 3600)}h</div><div className="kpi2-lbl">Purge sweep interval</div></div>
              </div>
              <div className="card2 kpi-row2">
                <div><div className="kpi2-val" style={{ fontSize: 16 }}>SQLite, single node</div><div className="kpi2-lbl">Storage backend</div></div>
              </div>
            </div>
            <p style={{ fontSize: 11.5, color: "var(--text-dim)", marginTop: 10, lineHeight: 1.6 }}>{retention.note}</p>
          </>
        )}
        {!retention && !error && <p style={{ color: "var(--text-dim)", fontSize: 12 }}>Loading…</p>}
      </div>

      <div className="card2" style={{ borderColor: "var(--border-strong)" }}>
        <div className="card-h2">
          <h2>Tiered storage — production design</h2>
          <StatusTag kind="DESIGN_TARGET" />
        </div>
        <p style={{ fontSize: 11.5, color: "var(--text-dim)", marginBottom: 10 }}>
          Not implemented. This pilot has one storage tier (SQLite + local disk crops) and
          the single retention window shown above — no hot/warm/cold split exists in code.
        </p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            { name: "HOT", desc: "Recent operational data — live search, active monitoring" },
            { name: "WARM", desc: "Active investigation data — open cases, recent evidence" },
            { name: "COLD", desc: "Archived evidentiary data — long-term retention, infrequent access" },
          ].map((t) => (
            <div key={t.name} className="card2" style={{ background: "var(--bg-sunken)", flex: "1 1 200px" }}>
              <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--text-dim)" }}>{t.name}</div>
              <div style={{ fontSize: 11.5, color: "var(--text-dim)", marginTop: 4 }}>{t.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
