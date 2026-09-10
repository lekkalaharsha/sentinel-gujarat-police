import MapView from "./MapView";

export default function LiveMapView({ cameras, route, selectedCameraId, onSelectCamera }) {
  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Live Map</h1>
          <div className="sub">Full statewide GIS canvas — real onboarded camera positions</div>
        </div>
      </div>
      <div className="card2" style={{ padding: 0 }}>
        <div className="mapwrap2" style={{ height: "calc(100vh - 190px)" }}>
          <div className="map-legend2">
            <span className="legend-item2"><span className="legend-swatch2" style={{ background: "var(--confirmed)" }} />Live</span>
            <span className="legend-item2"><span className="legend-swatch2" style={{ background: "#9ca3af" }} />Offline</span>
            <span className="legend-item2"><span className="legend-swatch2" style={{ background: "var(--predicted)" }} />Route stop</span>
          </div>
          <MapView cameras={cameras} route={route} selectedCameraId={selectedCameraId} onSelectCamera={onSelectCamera} />
        </div>
      </div>
    </>
  );
}
