import { useMemo, useState } from "react";
import MapView, { categoryColor } from "./MapView";

const LAYER_MODES = [
  { key: "health", label: "Health" },
  { key: "department", label: "Department" },
  { key: "camera_type", label: "Type" },
];

// Model 1 spec requires department/type/status/coverage map layers
// (REQUIREMENTS.md's R1) — health stays the default (matches prior
// behavior), department/type are togglable on top of it.
export default function LiveMapView({ cameras, route, selectedCameraId, onSelectCamera }) {
  const [mode, setMode] = useState("health");

  const categoryLegend = useMemo(() => {
    if (mode === "health") return null;
    const field = mode; // "department" | "camera_type"
    const values = new Set(cameras.map((c) => c[field] || null));
    return [...values]
      .sort((a, b) => (a || "").localeCompare(b || ""))
      .map((value) => ({
        label: value || (field === "department" ? "unassigned" : "unknown"),
        color: categoryColor(value),
      }));
  }, [cameras, mode]);

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Live Map</h1>
          <div className="sub">Full statewide GIS canvas — real onboarded camera positions</div>
        </div>
        <div className="map-layer-toggle2">
          {LAYER_MODES.map((m) => (
            <button
              key={m.key}
              className={`map-layer-btn2${mode === m.key ? " map-layer-btn2--active" : ""}`}
              onClick={() => setMode(m.key)}
              type="button"
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>
      <div className="card2" style={{ padding: 0 }}>
        <div className="mapwrap2" style={{ height: "calc(100vh - 190px)" }}>
          <div className="map-legend2">
            {mode === "health" ? (
              <>
                <span className="legend-item2"><span className="legend-swatch2" style={{ background: "var(--confirmed)" }} />Live</span>
                <span className="legend-item2"><span className="legend-swatch2" style={{ background: "#9ca3af" }} />Offline</span>
                <span className="legend-item2"><span className="legend-swatch2" style={{ background: "var(--predicted)" }} />Route stop</span>
              </>
            ) : (
              categoryLegend.length ? (
                categoryLegend.map((entry) => (
                  <span className="legend-item2" key={entry.label}>
                    <span className="legend-swatch2" style={{ background: entry.color }} />
                    {entry.label}
                  </span>
                ))
              ) : (
                <span className="legend-item2">No cameras onboarded yet</span>
              )
            )}
          </div>
          <MapView cameras={cameras} route={route} selectedCameraId={selectedCameraId} onSelectCamera={onSelectCamera} mode={mode} />
        </div>
      </div>
    </>
  );
}
