import { useRef, useState } from "react";
import { api } from "../api";

// Attribute-based search — GET /vehicle/search-by-attributes has existed on
// the backend since early in the build (the "plate never read anywhere"
// fallback) but had no frontend consumer until now.
export default function SearchView({ onOpenPlate }) {
  const [purpose, setPurpose] = useState("");
  const [vehicleType, setVehicleType] = useState("");
  const [color, setColor] = useState("");
  const [partialPlate, setPartialPlate] = useState("");
  const [caseId, setCaseId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef(null);

  async function submit(e) {
    e.preventDefault();
    if (!purpose) {
      setError("purpose is required — this is an audited lookup.");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchByAttributes(purpose.trim(), {
        vehicleType: vehicleType || undefined,
        color: color || undefined,
        partialPlate: partialPlate || undefined,
        caseId: caseId.trim() || undefined,
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setResult(data);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err.message);
      setResult(null);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return (
    <>
      <div className="view-head2">
        <div>
          <h1>Search</h1>
          <div className="sub">Attribute-based fallback — for when a plate was never read anywhere</div>
        </div>
      </div>

      <div className="card2" style={{ marginBottom: 14 }}>
        <div className="card-h2"><h2>Search by attributes</h2></div>
        <form onSubmit={submit} className="formgrid2">
          <div className="field2"><label>Purpose</label><input placeholder="stolen_vehicle_investigation" value={purpose} onChange={(e) => setPurpose(e.target.value)} /></div>
          <div className="field2">
            <label>Vehicle type</label>
            <select value={vehicleType} onChange={(e) => setVehicleType(e.target.value)}>
              <option value="">Any</option>
              <option value="car">Car</option>
              <option value="truck">Truck</option>
              <option value="bus">Bus</option>
              <option value="motorcycle">Motorcycle</option>
            </select>
          </div>
          <div className="field2"><label>Colour</label><input placeholder="white" value={color} onChange={(e) => setColor(e.target.value)} /></div>
          <div className="field2"><label>Partial plate</label><input placeholder="AB12" value={partialPlate} onChange={(e) => setPartialPlate(e.target.value)} /></div>
          <div className="field2"><label>Case ID (optional)</label><input value={caseId} onChange={(e) => setCaseId(e.target.value)} /></div>
          <div className="field2" style={{ display: "flex", alignItems: "flex-end" }}>
            <button className="btn2 primary2" type="submit" disabled={loading}>{loading ? "Searching…" : "Search"}</button>
          </div>
        </form>
        {error && <p style={{ color: "var(--danger)", fontSize: 11.5, marginTop: 8 }}>{error}</p>}
      </div>

      {result && (
        <div className="card2">
          <div className="card-h2"><h2>Results</h2><span className="n">{result.matches.length} match(es)</span></div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--text-dim)", fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  <th style={{ padding: "0 10px 8px" }}>Camera</th>
                  <th style={{ padding: "0 10px 8px" }}>Time</th>
                  <th style={{ padding: "0 10px 8px" }}>Plate</th>
                  <th style={{ padding: "0 10px 8px" }}>Type / colour</th>
                </tr>
              </thead>
              <tbody>
                {result.matches.map((m, i) => (
                  <tr
                    key={i}
                    style={{ borderBottom: "1px solid var(--border)", cursor: m.plate ? "pointer" : "default" }}
                    onClick={() => m.plate && onOpenPlate?.(m.plate)}
                  >
                    <td style={{ padding: "8px 10px", fontFamily: "var(--mono)" }}>{m.camera_id}</td>
                    <td style={{ padding: "8px 10px", fontFamily: "var(--mono)" }}>{new Date(m.observed_at).toLocaleString()}</td>
                    <td style={{ padding: "8px 10px", fontFamily: "var(--mono)" }}>{m.plate || <span style={{ color: "var(--text-dim)" }}>anonymous</span>}</td>
                    <td style={{ padding: "8px 10px" }}>{m.vehicle_type || "—"} · {m.color || "—"}</td>
                  </tr>
                ))}
                {!result.matches.length && (
                  <tr><td colSpan={4} style={{ padding: "10px", color: "var(--text-dim)" }}>No matches.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
