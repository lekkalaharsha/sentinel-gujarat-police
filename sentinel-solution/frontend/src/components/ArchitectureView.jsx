const STAGES = [
  { t: "CCTV / NVR / VMS", s: "RTSP · ONVIF · vendor APIs — this sandbox: direct RTSP" },
  { t: "Video ingestion", s: "Stream normalization, TCP-forced, PTS timing" },
  { t: "Vehicle detection", s: "YOLOv8n + ByteTrack (in-camera tracking)" },
  { t: "Plate localization + OCR", s: "Heuristic crop → CLAHE → PaddleOCR → regex validate → temporal fusion" },
  { t: "Vehicle Re-ID", s: "HSV colour-histogram appearance embedding" },
  { t: "Observation engine", s: "Camera + timestamp + evidence → persisted VehicleEvent" },
  { t: "Geo-temporal graph", s: "Real haversine feasibility filter over the onboarded registry", core: true },
  { t: "Identity fusion", s: "Plate-first, appearance-second cross-camera resolution" },
  { t: "Vehicle journey reconstruction", s: "OBSERVED / INFERRED / (feasibility-filtered) candidate states" },
];

// This screen is deliberately static — it documents the real pipeline
// (see HLD.md), it doesn't need to be "live" the way the operational
// screens do.
export default function ArchitectureView() {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>System Architecture</h1>
          <div className="sub">From raw feed to journey reconstruction — matches the actual code, see HLD.md</div>
        </div>
      </div>
      <div className="card2">
        <div className="arch2">
          {STAGES.map((st, i) => (
            <div key={st.t}>
              <div className={`arch2-node ${st.core ? "core2" : ""}`}><b>{st.t}</b><span>{st.s}</span></div>
              {i < STAGES.length - 1 && <div className="arch2-arrow">↓</div>}
            </div>
          ))}
          <div className="arch2-arrow">↓</div>
          <div className="arch2-branch">
            <div className="arch2-node"><b>GIS</b></div>
            <div className="arch2-node"><b>Search</b></div>
            <div className="arch2-node"><b>Alerts</b></div>
            <div className="arch2-node"><b>Reports</b></div>
          </div>
        </div>
      </div>
    </>
  );
}
