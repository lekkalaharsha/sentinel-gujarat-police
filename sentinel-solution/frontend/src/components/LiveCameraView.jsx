import { useEffect, useState } from "react";
import { api } from "../api";
import LiveView from "./LiveView";

const POLL_MS = 5000;

// GET /cameras/{id}/last-detection existed on the backend with no frontend
// consumer — this is NOT a live video overlay (the pipeline processes
// sampled frames server-side, it doesn't composite boxes onto the HLS
// stream), it's the real bbox/plate/attributes from the most recently
// processed frame, polled alongside the live player.
export default function LiveCameraView({ camera }) {
  const [detection, setDetection] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setDetection(null);
    if (!camera?.id) return;
    let cancelled = false;
    async function poll() {
      try {
        const data = await api.lastDetection(camera.id);
        if (!cancelled) { setDetection(data.detection); setError(null); }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, [camera?.id]);

  if (!camera) {
    return <p style={{ color: "var(--text-dim)" }}>Select a camera from the Camera Network screen to view its live feed.</p>;
  }

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Camera {camera.id}</h1>
          <div className="sub">{camera.location || "location unknown"} · {camera.live ? <span style={{ color: "var(--confirmed)" }}>● ONLINE</span> : <span style={{ color: "var(--danger)" }}>● OFFLINE</span>}</div>
        </div>
      </div>
      <div className="cols2">
        <div className="card2" style={{ padding: 10 }}>
          <LiveView cameraId={camera.id} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="card2">
            <div className="card-h2"><h2>Last processed detection</h2><span className="n">polled 5s</span></div>
            {error && <p style={{ color: "var(--danger)", fontSize: 11 }}>{error}</p>}
            {!detection && !error && <p style={{ color: "var(--text-dim)", fontSize: 11.5 }}>No detection recorded yet at this camera.</p>}
            {detection && (
              <>
                <div className="metarow2"><span>Time</span><b>{new Date(detection.observed_at).toLocaleTimeString()}</b></div>
                <div className="metarow2"><span>Plate</span><b>{detection.plate || "unread"}</b></div>
                <div className="metarow2"><span>Confidence</span><b>{detection.confidence != null ? `${Math.round(detection.confidence * 100)}%` : "—"}</b></div>
                <div className="metarow2" style={{ borderBottom: "none" }}><span>Type / colour</span><b>{detection.vehicle_type || "—"} · {detection.color || "—"}</b></div>
              </>
            )}
          </div>
          <div className="card2">
            <div className="card-h2"><h2>Camera metadata</h2></div>
            <div className="metarow2"><span>Camera ID</span><b>{camera.id}</b></div>
            <div className="metarow2"><span>GPS</span><b>{camera.latitude != null ? `${camera.latitude.toFixed(3)}, ${camera.longitude.toFixed(3)}` : "not registered"}</b></div>
            <div className="metarow2"><span>Department</span><b>{camera.department || "unassigned"}</b></div>
            <div className="metarow2" style={{ borderBottom: "none" }}><span>Health</span><b>{camera.is_healthy === true ? "Healthy" : camera.is_healthy === false ? "Unhealthy" : "Unknown"}</b></div>
          </div>
        </div>
      </div>
    </>
  );
}
