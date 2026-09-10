import { useEffect, useState } from "react";
import { api } from "../api";

export default function SettingsView() {
  const [identity, setIdentity] = useState(null);
  const [retention, setRetention] = useState(null);
  const [purgeResult, setPurgeResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.whoami().then(setIdentity).catch(() => setIdentity(null));
    api.retentionPolicy().then(setRetention).catch((err) => setError(err.message));
  }, []);

  async function runPurge() {
    setError(null);
    setPurgeResult(null);
    try {
      setPurgeResult(await api.triggerPurge());
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Settings</h1>
          <div className="sub">Access control and platform configuration</div>
        </div>
      </div>

      <div className="cols2">
        <div className="card2">
          <div className="card-h2"><h2>Your session</h2></div>
          {identity ? (
            <>
              <div className="metarow2"><span>User</span><b>{identity.user_id}</b></div>
              <div className="metarow2"><span>Role</span><b>{identity.role}</b></div>
              <div className="metarow2" style={{ borderBottom: "none" }}><span>Department</span><b>{identity.department || "none"}</b></div>
            </>
          ) : <p style={{ color: "var(--text-dim)", fontSize: 11.5 }}>Set an API key in the topbar to see your identity.</p>}
        </div>

        <div className="card2">
          <div className="card-h2"><h2>Retention policy</h2></div>
          {retention && (
            <>
              <div className="metarow2"><span>Event retention</span><b>{retention.vehicle_data_retention_days} days</b></div>
              <div className="metarow2" style={{ borderBottom: "none" }}><span>Audit log retention</span><b>{retention.audit_log_retention_days} days</b></div>
            </>
          )}
          <button className="btn2 danger2" style={{ marginTop: 12 }} onClick={runPurge}>Trigger purge now (admin)</button>
          {error && <p style={{ color: "var(--danger)", fontSize: 11, marginTop: 8 }}>{error}</p>}
          {purgeResult && <p style={{ color: "var(--confirmed)", fontSize: 11, marginTop: 8 }}>{JSON.stringify(purgeResult)}</p>}
        </div>
      </div>
    </>
  );
}
