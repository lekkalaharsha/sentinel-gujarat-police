import { useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Gujarat's rough centroid — used only as the map's default view when no
// camera has GIS coordinates yet (registry seeding is not in scope, see
// README's "GIS mapping (Model 1)" gap note).
const GUJARAT_CENTER = [22.2587, 71.1924];

// Must match backend's SENTINEL_CAMERA_AGEING_THRESHOLD_YEARS default
// (config.py) — display-only, not authoritative; the gap-analysis report
// is the source of truth for which cameras actually count as ageing.
const AGEING_THRESHOLD_YEARS = 5;

// Keep the evidence-tier language/colours aligned with VehicleTimeline.
// A LEAD_ONLY route point is an appearance-based investigative lead, not an
// observed movement; its connector must never look like direct evidence.
const ROUTE_STYLE = {
  CONFIRMED: { color: "#16a34a", dashArray: undefined },
  PROBABLE: { color: "#d97706", dashArray: undefined },
  LEAD_ONLY: { color: "#e02424", dashArray: "6 6" },
};

function markerColor(status) {
  if (status === "alert") return "#e02424";
  if (status === "route") return "#2563eb";
  if (status === "unhealthy") return "#9ca3af";
  return "#16a34a";
}

function isAgeing(installDate) {
  if (!installDate) return false;
  const ageYears = (Date.now() - new Date(installDate).getTime()) / (365.25 * 24 * 3600 * 1000);
  return ageYears > AGEING_THRESHOLD_YEARS;
}

export default function MapView({ cameras, route, onSelectCamera, selectedCameraId }) {
  const located = useMemo(
    () => cameras.filter((c) => c.latitude != null && c.longitude != null),
    [cameras]
  );
  const routePoints = useMemo(
    () =>
      (route || [])
        .filter((s) => s.latitude != null && s.longitude != null)
        .map((s) => [s.latitude, s.longitude]),
    [route]
  );

  const center = located.length
    ? [located[0].latitude, located[0].longitude]
    : routePoints.length
    ? [routePoints[0].latitude, routePoints[0].longitude]
    : GUJARAT_CENTER;

  return (
    <MapContainer center={center} zoom={routePoints.length ? 12 : 7} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {located.map((cam) =>
        cam.coverage_radius_m ? (
          <Circle
            key={`coverage-${cam.id}`}
            center={[cam.latitude, cam.longitude]}
            radius={cam.coverage_radius_m}
            pathOptions={{ color: "#2563eb", fillColor: "#2563eb", fillOpacity: 0.06, weight: 1 }}
          />
        ) : null
      )}
      {located.map((cam) => (
        <CircleMarker
          key={cam.id}
          center={[cam.latitude, cam.longitude]}
          radius={cam.id === selectedCameraId ? 10 : 7}
          pathOptions={{
            color: markerColor(cam.live ? "healthy" : "unhealthy"),
            fillColor: markerColor(cam.live ? "healthy" : "unhealthy"),
            fillOpacity: 0.85,
            dashArray: isAgeing(cam.install_date) ? "3 2" : undefined,
          }}
          eventHandlers={{ click: () => onSelectCamera?.(cam.id) }}
        >
          <Popup>
            <strong>{cam.id}</strong>
            <br />
            {cam.location || "location unknown"}
            <br />
            {cam.live ? "live" : "offline"} · {cam.codec || "codec unknown"}
            {cam.install_date && (
              <>
                <br />
                Installed {new Date(cam.install_date).toLocaleDateString()}
                {isAgeing(cam.install_date) && " (ageing)"}
              </>
            )}
          </Popup>
        </CircleMarker>
      ))}
      {routePoints.slice(1).map((point, i) => {
        const style = ROUTE_STYLE[point.evidence_class] || ROUTE_STYLE.LEAD_ONLY;
        return (
          <Polyline
            key={`route-segment-${i}`}
            positions={[[routePoints[i].latitude, routePoints[i].longitude], [point.latitude, point.longitude]]}
            pathOptions={{ color: style.color, weight: 3, dashArray: style.dashArray }}
          />
        );
      })}
      {routePoints.map((s, i) => {
          const style = ROUTE_STYLE[s.evidence_class] || ROUTE_STYLE.LEAD_ONLY;
          // Missing evidence_class must fail conservative (treated as
          // LEAD_ONLY/INFERRED), never default to the OBSERVED label —
          // matches evidence_class.py's own fail-conservative rule.
          const isLeadOnly = s.evidence_class == null || s.evidence_class === "LEAD_ONLY";
          return (
          <CircleMarker
            key={`route-${i}`}
            center={[s.latitude, s.longitude]}
            radius={9}
            pathOptions={{ color: style.color, fillColor: "#fff", fillOpacity: 1, weight: 3 }}
          >
            <Popup>
              <strong>Stop {i + 1}</strong> — {s.camera_id}
              <br />
              {s.location || "location unknown"}
              <br />
              {new Date(s.observed_at).toLocaleString()}
              <br />
              {isLeadOnly
                ? "Investigative Lead Only — Low Visual Confidence"
                : `${s.evidence_class} / OBSERVED`}
            </Popup>
          </CircleMarker>
          );
        })}
    </MapContainer>
  );
}
