// Renders the vehicle journey as CONFIRMED (OBSERVED) sightings interleaved
// with INFERRED camera-less segments (geo-temporal layer, see
// analytics/geo.py). The visual distinction is the point: a solid marker is
// real camera evidence; a dashed connector is an inference the operator must
// read as such, never as observed fact.
export default function VehicleTimeline({ sightings, routeSegments, selectedIndex, onSelect }) {
  if (!sightings?.length) {
    return <p className="timeline__empty">No movement history yet for this vehicle.</p>;
  }

  // Segments are keyed by the (from_camera -> to_camera) pair; find the one
  // bridging sighting i to i+1 (same-camera consecutive pairs have none).
  const segments = routeSegments || [];
  const segmentBetween = (from, to) =>
    segments.find((s) => s.from_camera === from && s.to_camera === to);

  return (
    <ol className="timeline">
      {sightings.map((s, i) => {
        const next = sightings[i + 1];
        const seg = next ? segmentBetween(s.camera_id, next.camera_id) : null;
        return (
          <li key={i} style={{ listStyle: "none" }}>
            <div
              className={`timeline__item ${i === selectedIndex ? "timeline__item--selected" : ""}`}
              onClick={() => onSelect(i)}
            >
              <div className="timeline__marker" />
              <div className="timeline__body">
                <div className="timeline__row">
                  <strong>{s.camera_id}</strong>
                  <span>{new Date(s.observed_at).toLocaleString()}</span>
                </div>
                <div className="timeline__row timeline__row--sub">
                  <span>{s.location || "unknown location"}</span>
                  <span>
                    {s.plate_read_at_this_camera ? (
                      <span className="badge badge--plate">plate read (consensus {Math.round((s.plate_confidence || 0) * 100)}%)</span>
                    ) : (
                      <span className="badge badge--anon">anonymous — matched by appearance</span>
                    )}
                  </span>
                </div>
                <div className="timeline__row timeline__row--sub">
                  <span>
                    {s.vehicle_type || "type unknown"} · {s.color || "colour unknown"}
                  </span>
                </div>
              </div>
            </div>
            {seg && (
              <div className={`timeline__inferred ${seg.plausible_direct_drive === false ? "timeline__inferred--implausible" : ""}`}>
                <span className="badge badge--inferred">inferred</span>{" "}
                {seg.distance_km != null ? (
                  <span>
                    ~{seg.distance_km} km · {Math.round(seg.time_gap_s)}s
                    {seg.implied_min_speed_kmh != null && <> · ≥{Math.round(seg.implied_min_speed_kmh)} km/h</>}
                    {seg.plausible_direct_drive === false && <strong> · not a direct drive</strong>}
                  </span>
                ) : (
                  <span>gap inferred from order only (no camera GIS)</span>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
