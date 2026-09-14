import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const POLL_MS = 5000;

// Governed alert lifecycle — mirrors the backend's ALERT_TRANSITIONS
// (COMPETITIVE_TEARDOWN.md §A / HLD §6). The UI only renders actions the
// server says are legal for the alert's current state (`allowed_transitions`),
// so the governance rule lives in exactly one place: the backend model.
const STATUS_LABEL = {
  new: "New",
  acknowledged: "Acknowledged",
  resolved: "Resolved",
  dismissed: "Dismissed (false positive)",
};
const TRANSITION_LABEL = {
  acknowledged: "Acknowledge",
  resolved: "Resolve",
  dismissed: "Dismiss (false +ve)",
};
// Named anomaly alerts (analytics/anomaly.py) vs. the original watchlist
// match — same governed lifecycle, just a different trigger, so badged
// rather than given a separate panel.
const ALERT_TYPE_LABEL = {
  watchlist: "Watchlist match",
  wrong_way: "Wrong-way vehicle",
  stopped_restricted_zone: "Stopped in restricted zone",
};

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [pendingIds, setPendingIds] = useState([]);
  const pendingTransitions = useRef(new Set());

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const data = await api.listAlerts();
        if (!cancelled) {
          // A poll started before a status mutation can return stale data.
          // Preserve the local row while its own transition is unresolved.
          setAlerts((previous) => data.map((incoming) => {
            const local = previous.find((alert) => alert.id === incoming.id);
            return pendingTransitions.current.has(incoming.id) && local ? local : incoming;
          }));
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  async function transition(id, status) {
    if (pendingTransitions.current.has(id)) return;
    pendingTransitions.current.add(id);
    setPendingIds((previous) => [...previous, id]);
    try {
      const updated = await api.setAlertStatus(id, status);
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, ...updated } : a)));
      setError(null);
    } catch (err) {
      if (String(err.message).startsWith("409")) {
        setError("This alert was already updated. Refreshing the alert list…");
        try {
          setAlerts(await api.listAlerts());
        } catch {
          // Keep the useful transition message instead of a raw error.
        }
      } else {
        setError(err.message);
      }
    } finally {
      pendingTransitions.current.delete(id);
      setPendingIds((previous) => previous.filter((pendingId) => pendingId !== id));
    }
  }

  // "Open" = still needs an operator: anything not in a terminal state.
  const open = alerts.filter((a) => (a.status || "new") === "new" || (a.status || "new") === "acknowledged");

  return (
    <div className="alerts-panel">
      <h3>
        Watchlist alerts {open.length > 0 && <span className="alerts-panel__count">{open.length}</span>}
      </h3>
      {error && <p className="alerts-panel__error">{error}</p>}
      {!alerts.length && !error && <p className="alerts-panel__empty">No alerts yet.</p>}
      <ul>
        {alerts.map((a) => {
          const status = a.status || "new";
          const transitions = a.allowed_transitions || [];
          return (
            <li key={a.id} className={`alert-item alert-item--${status}`}>
              <div>
                <span className={`alert-item__type alert-item__type--${a.alert_type || "watchlist"}`}>
                  {ALERT_TYPE_LABEL[a.alert_type] || a.alert_type || "Watchlist match"}
                </span>
                <strong>{a.plate}</strong> at <strong>{a.camera_id}</strong>
                <div className="alert-item__reason">{a.reason}</div>
                <div className="alert-item__time">{new Date(a.created_at).toLocaleString()}</div>
                <div className={`alert-item__status alert-item__status--${status}`}>
                  {STATUS_LABEL[status] || status}
                  {a.status_updated_by && (
                    <span className="alert-item__status-by"> · by {a.status_updated_by}</span>
                  )}
                </div>
              </div>
              {transitions.length > 0 && (
                <div className="alert-item__actions">
                  {transitions.map((t) => (
                    <button
                      key={t}
                      onClick={() => transition(a.id, t)}
                      disabled={pendingIds.includes(a.id)}
                      className={`alert-item__action alert-item__action--${t}`}
                    >
                      {TRANSITION_LABEL[t] || t}
                    </button>
                  ))}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
