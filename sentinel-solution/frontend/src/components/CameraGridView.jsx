import { useMemo, useState } from "react";
import LiveView from "./LiveView";

// Model 2's "configurable video wall" bonus deliverable — previously
// CameraNetworkView's "grid" was a layout of metadata CARDS, not live
// video tiles (found in MODULE_GAP_ANALYSIS.md 2026-09-05). This is the
// real thing: N simultaneous HLS tiles, each its own LiveView instance
// (own hls.js session, own auth headers, own error state — see LiveView's
// docstring), so one camera's stream error never affects the others.
//
// Capped, not unbounded: each tile is a real hls.js session against the
// backend's authenticated proxy (routes_stream.py) — opening dozens at
// once would multiply backend load same as opening that many browser tabs
// would. MAX_TILES is a UI guard, not a backend limit; a real deployment's
// actual concurrency ceiling is a bandwidth/CPU question for SCALABILITY.md,
// not something this component should silently pretend doesn't exist.
const MAX_TILES = 9;

export default function CameraGridView({ cameras }) {
  const liveCameras = useMemo(() => cameras.filter((c) => c.live), [cameras]);
  const [selected, setSelected] = useState([]);

  function toggle(id) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_TILES) return prev; // silently ignore past the cap, not an error state
      return [...prev, id];
    });
  }

  function selectFirstN(n) {
    setSelected(liveCameras.slice(0, n).map((c) => c.id));
  }

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Camera Grid</h1>
          <div className="sub">
            Synchronized multi-camera live view — {selected.length}/{MAX_TILES} tiles active,
            {" "}{liveCameras.length} cameras currently live
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn2" onClick={() => selectFirstN(4)}>First 4</button>
          <button className="btn2" onClick={() => selectFirstN(9)}>First 9</button>
          <button className="btn2" onClick={() => setSelected([])}>Clear</button>
        </div>
      </div>

      <div className="cols2" style={{ marginBottom: 14 }}>
        <div className="card2" style={{ maxHeight: 220, overflowY: "auto" }}>
          <div className="card-h2"><h2>Select cameras</h2><span className="n">click to toggle, up to {MAX_TILES}</span></div>
          <div className="camera-grid-picker">
            {liveCameras.length === 0 && <p style={{ color: "var(--text-dim)", fontSize: 12 }}>No live cameras right now.</p>}
            {liveCameras.map((c) => (
              <button
                key={c.id}
                onClick={() => toggle(c.id)}
                className={`camera-grid-picker__chip ${selected.includes(c.id) ? "camera-grid-picker__chip--active" : ""}`}
              >
                {c.id}
              </button>
            ))}
          </div>
        </div>
      </div>

      {selected.length === 0 ? (
        <div className="card2" style={{ padding: 24, textAlign: "center", color: "var(--text-dim)" }}>
          Select one or more live cameras above to tile their feeds.
        </div>
      ) : (
        <div className={`camera-grid camera-grid--n${selected.length}`}>
          {selected.map((id) => (
            <div key={id} className="camera-grid__tile card2">
              <div className="camera-grid__tile-label">{id}</div>
              <LiveView cameraId={id} />
            </div>
          ))}
        </div>
      )}
    </>
  );
}
