import { useState } from "react";
import MapView from "./MapView";
import CameraList from "./CameraList";
import GapAnalysisPanel from "./GapAnalysisPanel";
import OnboardCameraForm from "./OnboardCameraForm";
import BulkOnboardForm from "./BulkOnboardForm";
import { IconCamera, IconAlert, IconMap } from "../icons";

export default function CameraNetworkView({ cameras, gapAnalysis, selectedCameraId, onSelectCamera, onOnboarded, gapRefreshToken }) {
  const [mapOpen, setMapOpen] = useState(false);
  const online = cameras.filter((c) => c.live).length;
  const withDept = cameras.filter((c) => c.department).length;

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Camera Network</h1>
          <div className="sub">Statewide CCTV infrastructure / {cameras.length} cameras known to the catalogue</div>
        </div>
        <button className="btn2 primary2 camera-network-map-button" onClick={() => setMapOpen(true)}><IconMap width={15} height={15} /> Open live map</button>
      </div>

      <div className="grid4">
        <div className="card2 kpi-row2">
          <div className="stat-icon2 i-confirmed"><IconCamera /></div>
          <div><div className="kpi2-val" style={{ color: "var(--confirmed)" }}>{online}</div><div className="kpi2-lbl">Online</div></div>
        </div>
        <div className="card2 kpi-row2">
          <div className="stat-icon2 i-accent"><IconCamera /></div>
          <div><div className="kpi2-val">{gapAnalysis?.registered_size ?? cameras.length}</div><div className="kpi2-lbl">Registered (Model 1)</div></div>
        </div>
        <div className="card2 kpi-row2">
          <div className="stat-icon2 i-predicted"><IconCamera /></div>
          <div><div className="kpi2-val">{withDept}</div><div className="kpi2-lbl">Department-tagged</div></div>
        </div>
        <div className="card2 kpi-row2">
          <div className="stat-icon2 i-danger"><IconAlert /></div>
          <div><div className="kpi2-val" style={{ color: "var(--danger)" }}>{gapAnalysis?.unhealthy?.length ?? 0}</div><div className="kpi2-lbl">Unhealthy</div></div>
        </div>
      </div>

      <div className="card2 camera-network-registry" style={{ marginBottom: 14, maxHeight: 480, overflowY: "auto" }}>
        <CameraList cameras={cameras} selectedCameraId={selectedCameraId} onSelectCamera={onSelectCamera} />
      </div>

      {mapOpen && <div className="camera-map-modal" role="dialog" aria-modal="true" aria-label="Camera GIS map"><div className="camera-map-modal__backdrop" onClick={() => setMapOpen(false)} /><div className="camera-map-modal__panel"><div className="camera-map-modal__head"><div><h2>Camera GIS map</h2><span className="sub">Registry coordinates / click a pin to inspect it</span></div><button className="btn2" onClick={() => setMapOpen(false)}>Close</button></div><div className="mapwrap2"><MapView cameras={cameras} onSelectCamera={onSelectCamera} selectedCameraId={selectedCameraId} /></div></div></div>}

      <div className="cols2">
        <GapAnalysisPanel onRefresh={gapRefreshToken} />
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <OnboardCameraForm onOnboarded={onOnboarded} />
          <BulkOnboardForm onOnboarded={onOnboarded} />
        </div>
      </div>
    </>
  );
}
