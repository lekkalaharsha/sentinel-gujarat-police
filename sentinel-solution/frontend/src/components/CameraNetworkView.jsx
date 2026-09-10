import MapView from "./MapView";
import CameraList from "./CameraList";
import GapAnalysisPanel from "./GapAnalysisPanel";
import OnboardCameraForm from "./OnboardCameraForm";
import { IconCamera, IconAlert } from "../icons";

export default function CameraNetworkView({ cameras, gapAnalysis, selectedCameraId, onSelectCamera, onOnboarded, gapRefreshToken, onOpenCamera }) {
  const online = cameras.filter((c) => c.live).length;
  const withDept = cameras.filter((c) => c.department).length;

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Camera Network</h1>
          <div className="sub">Statewide CCTV infrastructure — {cameras.length} cameras known to the catalogue</div>
        </div>
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

      <div className="cols2" style={{ marginBottom: 14 }}>
        <div className="card2" style={{ padding: 0 }}>
          <div className="mapwrap2">
            <MapView cameras={cameras} onSelectCamera={(id) => { onSelectCamera(id); onOpenCamera?.(id); }} selectedCameraId={selectedCameraId} />
          </div>
        </div>
        <div className="card2" style={{ maxHeight: 480, overflowY: "auto" }}>
          <CameraList cameras={cameras} selectedCameraId={selectedCameraId} onSelectCamera={onSelectCamera} />
        </div>
      </div>

      <div className="cols2">
        <GapAnalysisPanel onRefresh={gapRefreshToken} />
        <OnboardCameraForm onOnboarded={onOnboarded} />
      </div>
    </>
  );
}
