import { useState } from "react";
import { api } from "../api";
import VehicleTimeline from "./VehicleTimeline";
import ExplainabilityPanel from "./ExplainabilityPanel";

// Purpose-bound query: every lookup requires a stated purpose, logged
// against the AUTHENTICATED user from the API key (see routes_vehicle.py) —
// "who" comes from RBAC now, not a self-reported field, so the audit trail
// can't be spoofed by typing someone else's name.
export default function VehicleSearch({ onResult }) {
  const [plate, setPlate] = useState("");
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
      onResult?.(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="vehicle-search">
      <form onSubmit={submit} className="vehicle-search__form">
        <input placeholder="Plate (e.g. GJ01AB1234)" value={plate} onChange={(e) => setPlate(e.target.value)} />
        <input placeholder="Purpose (e.g. stolen_vehicle_investigation)" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
        <input placeholder="Case ID (optional)" value={caseId} onChange={(e) => setCaseId(e.target.value)} />
        <button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>
      {error && <p className="vehicle-search__error">{error}</p>}
      {result && (
        <>
          {result.note && <p className="vehicle-search__note">{result.note}</p>}
          <VehicleTimeline
            sightings={result.sightings}
            routeSegments={result.route_segments}
            selectedIndex={selectedIndex}
            onSelect={setSelectedIndex}
          />
          {selectedIndex != null && result.sightings?.[selectedIndex] && (
            <ExplainabilityPanel sighting={result.sightings[selectedIndex]} />
          )}
        </>
      )}
    </div>
  );
}
