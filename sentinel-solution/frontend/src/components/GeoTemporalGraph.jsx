import { useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../api";

const GUJARAT_CENTER = [22.2587, 71.1924];

export default function GeoTemporalGraph({ cameras, initialPlate }) {
  const [plate, setPlate] = useState(initialPlate || "");
  const [purpose, setPurpose] = useState("");
  const [caseId, setCaseId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const camerasById = useMemo(() => {
    const m = {};
    for (const c of cameras || []) m[c.id] = c;
    return m;
  }, [cameras]);

  async function submit(e) {
    e.preventDefault();
    if (!plate || !purpose) {
      setError("plate and purpose are required — this is an audited lookup, same as vehicle history.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await api.candidateCameras(plate.trim(), purpose.trim(), caseId.trim() || undefined));
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const feasible = (result?.candidates || []).filter((c) => c.status === "FEASIBLE");
  const eliminated = (result?.candidates || []).filter((c) => c.status === "ELIMINATED");
  const lastCam = result?.last_known_camera ? camerasById[result.last_known_camera] : null;

  const mapCenter = lastCam?.latitude != null ? [lastCam.latitude, lastCam.longitude] : GUJARAT_CENTER;
  const plottable = feasible.filter((c) => camerasById[c.camera_id]?.latitude != null);

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Geo-Temporal Graph <span className="state-badge state-badge--predicted">Core engine</span></h1>
          <div className="sub">Real physics-based feasibility over the actual onboarded camera registry — not a learned prediction</div>
        </div>
      </div>

      <div className="card2" style={{ marginBottom: 14 }}>
        <div className="card-h2"><h2>Run the search</h2></div>
        <form onSubmit={submit} className="formgrid2">
          <div className="field2"><label>Plate</label><input placeholder="GJ01AB1234" value={plate} onChange={(e) => setPlate(e.target.value)} /></div>
          <div className="field2"><label>Purpose</label><input placeholder="stolen_vehicle_investigation" value={purpose} onChange={(e) => setPurpose(e.target.value)} /></div>
          <div className="field2"><label>Case ID (optional)</label><input value={caseId} onChange={(e) => setCaseId(e.target.value)} /></div>
          <div className="field2" style={{ display: "flex", alignItems: "flex-end" }}>
            <button className="btn2 primary2" type="submit" disabled={loading}>{loading ? "Running…" : "Find candidate cameras"}</button>
          </div>
        </form>
        {error && <p style={{ color: "var(--danger)", fontSize: 11.5, marginTop: 8 }}>{error}</p>}
      </div>

      {result?.note && <div className="honest2">{result.note}</div>}

      {result && result.candidates && (
        <>
          {/* Pipeline strip — filled with REAL numbers from this actual run, not illustrative placeholders. */}
          <div className="card2" style={{ marginBottom: 14 }}>
            <div className="card-h2"><h2>Resolution pipeline — this run</h2></div>
            <div className="pipeline2">
              <div className="pstep2"><div className="pn2">01</div><div className="pt2">Last observation</div><div className="pd2">{result.last_known_camera} · {new Date(result.last_known_at).toLocaleTimeString()}</div></div>
              <div className="pstep2"><div className="pn2">02</div><div className="pt2">Graph search</div><div className="pd2">{cameras?.length ?? "?"} registered cameras evaluated</div></div>
              <div className="pstep2"><div className="pn2">03</div><div className="pt2">Feasibility filter</div><div className="pd2">Haversine distance ÷ elapsed time vs. plausible max speed</div></div>
              <div className="pstep2"><div className="pn2">04</div><div className="pt2">Candidates</div><div className="pd2">{feasible.length} feasible, {eliminated.length} eliminated</div></div>
              <div className="pstep2"><div className="pn2">05</div><div className="pt2">Next step</div><div className="pd2">OCR + Re-ID would run only on feasible cameras</div></div>
            </div>
            <p style={{ fontSize: 10.5, color: "var(--text-dim)", marginTop: 8, marginBottom: 0 }}>{result.method}</p>
          </div>

          <div className="cols3-2">
            <div className="card2" style={{ padding: 0 }}>
              <div className="mapwrap2" style={{ height: 440 }}>
                <MapContainer center={mapCenter} zoom={lastCam ? 10 : 7} style={{ height: "100%", width: "100%" }}>
                  <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  {lastCam?.latitude != null && (
                    <CircleMarker center={[lastCam.latitude, lastCam.longitude]} radius={11} pathOptions={{ color: "#22c55e", fillColor: "#22c55e", fillOpacity: 0.9 }}>
                      <Popup><strong>{lastCam.id}</strong> — last observation<br />{lastCam.location}</Popup>
                    </CircleMarker>
                  )}
                  {plottable.map((c) => {
                    const cam = camerasById[c.camera_id];
                    return (
                      <CircleMarker key={c.camera_id} center={[cam.latitude, cam.longitude]} radius={9} pathOptions={{ color: "#3b82f6", fillColor: "#3b82f6", fillOpacity: 0.5, dashArray: "4 3" }}>
                        <Popup><strong>{c.camera_id}</strong> — feasible candidate<br />{c.distance_km} km · ≥{c.required_min_speed_kmh} km/h required</Popup>
                      </CircleMarker>
                    );
                  })}
                </MapContainer>
                {!lastCam?.latitude && (
                  <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(10,13,18,0.7)", color: "var(--text-dim)", fontSize: 12, textAlign: "center", padding: 20 }}>
                    Last-known camera {result.last_known_camera} has no GIS coordinates registered — map plotting needs onboarded GPS.
                  </div>
                )}
              </div>
            </div>

            <div className="card2">
              <div className="card-h2"><h2>Last observation</h2></div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 16, fontWeight: 800, color: "var(--text-h)" }}>{result.last_known_camera}</div>
              <div style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 10 }}>{lastCam?.location || "location unknown"}</div>
              <div className="metarow2"><span>Time</span><b>{new Date(result.last_known_at).toLocaleString()}</b></div>
            </div>

            <div className="card2">
              <div className="card-h2"><h2>Candidate cameras</h2><span className="n">{feasible.length} of {result.candidates.length}</span></div>
              <div className="candlist2">
                {feasible.map((c) => (
                  <div className="cand2" key={c.camera_id}>
                    <div><div className="camid2">{c.camera_id}</div><div className="sub2">{c.distance_km} km · ≥{c.required_min_speed_kmh} km/h</div></div>
                    <div className="feas2 feasible2">FEASIBLE</div>
                  </div>
                ))}
                {!feasible.length && <p style={{ fontSize: 11, color: "var(--text-dim)" }}>No feasible candidates — either no other registered cameras are reachable, or none have GPS.</p>}
              </div>
              {eliminated.length > 0 && (
                <>
                  <div className="hr" style={{ height: 1, background: "var(--border)", margin: "10px 0" }} />
                  <div style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-dim)", marginBottom: 6 }}>Eliminated ({eliminated.length})</div>
                  {eliminated.slice(0, 5).map((c) => (
                    <div className="cand2 eliminated2" key={c.camera_id}>
                      <div><div className="camid2">{c.camera_id}</div><div className="sub2">≥{c.required_min_speed_kmh} km/h required</div></div>
                      <div className="feas2 eliminated2">RULED OUT</div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
