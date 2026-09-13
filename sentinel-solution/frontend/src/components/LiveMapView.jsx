import { useMemo, useState } from "react";
import LiveView from "./LiveView";
import SnapshotView from "./SnapshotView";
import CameraDetailPanel from "./CameraDetailPanel";

const MAX_TILES = 6;

function healthOf(camera) {
  if (camera.analytics_degraded === true) return "degraded";
  if (camera.is_healthy === true) return "healthy";
  if (camera.is_healthy === false) return "offline";
  return "unknown";
}

export default function LiveMapView({ cameras }) {
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("");
  const [source, setSource] = useState("");
  const [healthFilter, setHealthFilter] = useState("");
  const [cameraType, setCameraType] = useState("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState([]);
  const [tileLimit, setTileLimit] = useState(4);
  const [detailCameraId, setDetailCameraId] = useState(null);

  const departments = useMemo(() => [...new Set(cameras.map((camera) => camera.department || "Unassigned"))].sort(), [cameras]);
  const cameraTypes = useMemo(() => [...new Set(cameras.map((camera) => camera.camera_type).filter(Boolean))].sort(), [cameras]);
  const locations = useMemo(() => [...new Set(cameras.map((camera) => camera.location).filter(Boolean))].sort(), [cameras]);
  const filteredCameras = useMemo(() => cameras.filter((camera) => {
    const searchText = `${camera.id} ${camera.location || ""} ${camera.vendor || ""}`.toLowerCase();
    const feedSource = camera.source_system ? "external" : camera.live ? "live" : "offline";
    return (!department || (camera.department || "Unassigned") === department)
      && (!location || camera.location === location)
      && (!source || feedSource === source)
      && (!healthFilter || healthOf(camera) === healthFilter)
      && (!cameraType || camera.camera_type === cameraType)
      && (!query || searchText.includes(query.toLowerCase()));
  }), [cameras, department, location, source, healthFilter, cameraType, query]);
  const viewableCameras = useMemo(() => filteredCameras.filter((camera) => camera.live || camera.snapshot_image_url), [filteredCameras]);
  const viewableById = useMemo(() => Object.fromEntries(viewableCameras.map((camera) => [camera.id, camera])), [viewableCameras]);
  const activeSelected = selected.filter((id) => viewableById[id]);

  function updateFilter(setter) {
    return (event) => { setter(event.target.value); setSelected([]); };
  }
  function toggle(id) {
    setSelected((previous) => {
      const active = previous.filter((cameraId) => viewableById[cameraId]);
      return active.includes(id) ? active.filter((cameraId) => cameraId !== id) : active.length < tileLimit ? [...active, id] : active;
    });
  }
  function setWallLimit(limit) {
    setTileLimit(limit);
    setSelected((previous) => previous.filter((id) => viewableById[id]).slice(0, limit));
  }

  return <>
    <div className="view-head2"><div><h1>Live Network</h1><div className="sub">Live and external camera feeds for Gujarat operations.</div></div></div>
    <div className="card2 live-network-filter">
      <label>Department<select value={department} onChange={updateFilter(setDepartment)}><option value="">All departments</option>{departments.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
      <label>Location<select value={location} onChange={updateFilter(setLocation)}><option value="">All locations</option>{locations.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
      <label>Feed source<select value={source} onChange={updateFilter(setSource)}><option value="">All sources</option><option value="live">Live HLS</option><option value="external">External snapshots</option><option value="offline">Offline / unavailable</option></select></label>
      <label>Health<select value={healthFilter} onChange={updateFilter(setHealthFilter)}><option value="">All health states</option><option value="healthy">Healthy</option><option value="degraded">Analytics degraded</option><option value="offline">Unhealthy</option><option value="unknown">Unknown</option></select></label>
      <label>Camera type<select value={cameraType} onChange={updateFilter(setCameraType)}><option value="">All camera types</option>{cameraTypes.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
      <label className="live-network-filter__search">Search<input value={query} onChange={updateFilter(setQuery)} placeholder="ID, location, vendor" /></label>
      <span>State: Gujarat</span>
    </div>
    <div className="card2 camera-registry-list">
      <div className="camera-registry-list__head"><div><h2>Camera registry</h2><span className="sub">{filteredCameras.length} cameras match the metadata filters</span></div><span className="sub">Real registry metadata</span></div>
      <div className="camera-registry-table-wrap"><table className="camera-registry-table"><thead><tr><th>Camera</th><th>Department</th><th>Location</th><th>Type / vendor</th><th>Feed</th><th>Health</th></tr></thead><tbody>{filteredCameras.map((camera) => { const health = healthOf(camera); return <tr key={camera.id}><td><strong>{camera.id}</strong></td><td>{camera.department || "Unassigned"}</td><td>{camera.location || "Location unknown"}</td><td>{camera.camera_type || "Type unknown"}{camera.vendor ? ` / ${camera.vendor}` : ""}</td><td>{camera.source_system ? "External snapshot" : camera.live ? "Live HLS" : "Offline"}</td><td><span className={`camera-health-dot camera-health-dot--${health}`} />{health}</td></tr>; })}</tbody></table>{filteredCameras.length === 0 && <p className="sub camera-registry-list__empty">No cameras match these metadata filters.</p>}</div>
    </div>
    <div className="view-head2 live-network-wall-head"><div><h2>Video wall</h2><div className="sub">{activeSelected.length}/{tileLimit} tiles active / {viewableCameras.length} selectable cameras</div></div><div style={{ display: "flex", gap: 8 }}><button className="btn2" onClick={() => setWallLimit(4)}>4</button><button className="btn2" onClick={() => setWallLimit(MAX_TILES)}>6</button><button className="btn2" onClick={() => setSelected([])}>Clear</button></div></div>
    <div className="card2" style={{ marginBottom: 14 }}><div className="camera-grid-picker">{viewableCameras.length === 0 ? <p className="sub">No viewable cameras match the current filters.</p> : viewableCameras.map((camera) => <button key={camera.id} onClick={() => toggle(camera.id)} className={`camera-grid-picker__chip ${activeSelected.includes(camera.id) ? "camera-grid-picker__chip--active" : ""}`}>{camera.id}{camera.source_system ? " (external)" : ""}</button>)}</div></div>
    {activeSelected.length === 0 ? <div className="card2" style={{ padding: 24, textAlign: "center", color: "var(--text-dim)" }}>Select one or more filtered cameras to tile their feeds.</div> : <div className={`camera-grid camera-grid--n${activeSelected.length}`}>{activeSelected.map((id) => { const camera = viewableById[id]; return <div key={id} className="camera-grid__tile card2"><div className="camera-grid__tile-label">{id}</div><button className="camera-grid__tile-info" aria-label={`Open details for ${id}`} onClick={() => setDetailCameraId(id)}>i</button>{camera.snapshot_image_url ? <SnapshotView imageUrl={camera.snapshot_image_url} sourceLabel={camera.source_system} /> : <LiveView cameraId={id} />}</div>; })}</div>}
    {detailCameraId && <CameraDetailPanel cameraId={detailCameraId} onClose={() => setDetailCameraId(null)} />}
  </>;
}
