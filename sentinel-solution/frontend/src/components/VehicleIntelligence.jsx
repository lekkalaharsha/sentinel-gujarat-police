import { useState } from "react";
import { api } from "../api";
import VehicleTimeline from "./VehicleTimeline";
import ExplainabilityPanel from "./ExplainabilityPanel";
import EvidenceViewer from "./EvidenceViewer";
import { IconVehicleSide } from "../icons";

export default function VehicleIntelligence({ initialPlate, onResult, onOpenGraph }) {
  const [plate, setPlate] = useState(initialPlate || "");
  const [purpose, setPurpose] = useState("");
  const [caseId, setCaseId] = useState("");
  const [result, setResult] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    if (!plate || !purpose) {
      setError("plate and purpose are required — every query is audit-logged against your API key.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.vehicleHistory(plate.trim(), purpose.trim(), caseId.trim() || undefined);
      setResult(data);
      setSelectedIndex(data.sightings?.length ? data.sightings.length - 1 : null);
      onResult?.(data);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const selected = selectedIndex != null ? result?.sightings?.[selectedIndex] : null;
  const latest = result?.sightings?.[result.sightings.length - 1];

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Vehicle Intelligence</h1>
          <div className="sub">Complete cross-camera movement history — the core evaluation ask</div>
        </div>
        {result?.plate && (
          <div className="view-actions">
            <button className="btn2 primary2" onClick={() => onOpenGraph?.(result.plate)}>Open in Geo-Temporal Graph</button>
          </div>
        )}
      </div>

      <div className="cols2">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="card2">
            <div className="card-h2"><h2>Search</h2></div>
            <form onSubmit={submit} className="formgrid2">
              <div className="field2"><label>Plate</label><input placeholder="GJ01AB1234" value={plate} onChange={(e) => setPlate(e.target.value)} /></div>
              <div className="field2"><label>Purpose</label><input placeholder="stolen_vehicle_investigation" value={purpose} onChange={(e) => setPurpose(e.target.value)} /></div>
              <div className="field2"><label>Case ID (optional)</label><input value={caseId} onChange={(e) => setCaseId(e.target.value)} /></div>
              <div className="field2" style={{ display: "flex", alignItems: "flex-end" }}>
                <button className="btn2 primary2" type="submit" disabled={loading}>{loading ? "Searching…" : "Search"}</button>
              </div>
            </form>
            {error && <p style={{ color: "var(--danger)", fontSize: 11.5, marginTop: 8 }}>{error}</p>}
          </div>

          {result && (
            <div className="card2">
              <div className="card-h2"><h2>Journey reconstruction</h2><span className="n">{result.sightings.length} sighting(s)</span></div>
              {result.note && <p style={{ color: "var(--text-dim)", fontSize: 11.5 }}>{result.note}</p>}
              <VehicleTimeline sightings={result.sightings} routeSegments={result.route_segments} selectedIndex={selectedIndex} onSelect={setSelectedIndex} />
            </div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {result?.plate && (
            <div className="card2">
              <div className="card-h2"><h2>Vehicle</h2></div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <div className="vehicle-thumb2"><IconVehicleSide /></div>
                <div className="plate-graphic2"><div className="plate-band2">IND</div><div className="plate-num2">{result.plate}</div></div>
              </div>
              {latest && (
                <>
                  <div className="metarow2"><span>Type / colour</span><b>{latest.vehicle_type || "unknown"} · {latest.color || "unknown"}</b></div>
                  <div className="metarow2" style={{ borderBottom: "none" }}><span>First seen</span><b>{new Date(result.identity_first_seen).toLocaleString()}</b></div>
                </>
              )}
            </div>
          )}

          {selected && (
            <>
              <EvidenceViewer eventId={selected.event_id} hasImage={selected.has_evidence_image} label={`Evidence · ${selected.camera_id}`} />
              <ExplainabilityPanel sighting={selected} />
            </>
          )}
        </div>
      </div>
    </>
  );
}
