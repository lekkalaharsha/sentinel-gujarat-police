import { useEffect, useState } from "react";
import { api } from "../api";
import EvidenceViewer from "./EvidenceViewer";

export default function EvidenceView() {
  const [events, setEvents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.recentDetections(30).then(setEvents).catch((err) => setError(err.message));
  }, []);

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Evidence</h1>
          <div className="sub">Real saved detection crops — suitable for investigation review, not a mockup gallery</div>
        </div>
      </div>
      <div className="cols2">
        <div className="card2" style={{ maxHeight: 560, overflowY: "auto" }}>
          <div className="card-h2"><h2>Recent events</h2></div>
          {error && <p style={{ color: "var(--danger)", fontSize: 11 }}>{error}</p>}
          {events.map((e) => (
            <div
              key={e.event_id}
              className="detectrow2"
              style={{ cursor: "pointer", background: selected?.event_id === e.event_id ? "var(--accent-bg)" : "transparent" }}
              onClick={() => setSelected(e)}
            >
              <div className="info2">
                <div className="plate2">{e.plate || `${e.color || "?"} ${e.vehicle_type || "vehicle"}`}</div>
                <div className="meta2">{new Date(e.observed_at).toLocaleString()} · {e.camera_id}</div>
              </div>
              {e.has_evidence_image && <span className="state-badge state-badge--confirmed">has image</span>}
            </div>
          ))}
          {!events.length && !error && <p style={{ color: "var(--text-dim)", fontSize: 11.5 }}>No events yet.</p>}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {selected ? (
            <>
              <EvidenceViewer eventId={selected.event_id} hasImage={selected.has_evidence_image} label={`Evidence · ${selected.camera_id}`} />
              <div className="card2">
                <div className="card-h2"><h2>Metadata</h2></div>
                <div className="metarow2"><span>Camera ID</span><b>{selected.camera_id}</b></div>
                <div className="metarow2"><span>Location</span><b>{selected.location || "unknown"}</b></div>
                <div className="metarow2"><span>Timestamp</span><b>{new Date(selected.observed_at).toLocaleString()}</b></div>
                <div className="metarow2"><span>Plate</span><b>{selected.plate || "unread"}</b></div>
                <div className="metarow2"><span>Plate consensus strength</span><b>{selected.plate_confidence != null ? `${Math.round(selected.plate_confidence * 100)}%` : "—"}</b></div>
                <div className="metarow2" style={{ borderBottom: "none" }}><span>Watchlist status</span><b style={{ color: selected.watchlisted ? "var(--danger)" : "var(--text-h)" }}>{selected.watchlisted ? "Watchlisted" : "Not watchlisted"}</b></div>
              </div>
            </>
          ) : (
            <p style={{ color: "var(--text-dim)", fontSize: 12 }}>Select an event to view its evidence image and metadata.</p>
          )}
        </div>
      </div>
    </>
  );
}
