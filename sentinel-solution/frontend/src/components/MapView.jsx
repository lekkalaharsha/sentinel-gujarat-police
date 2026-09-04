import { useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Gujarat's rough centroid — used only as the map's default view when no
// camera has GIS coordinates yet (registry seeding is not in scope, see
// README's "GIS mapping (Model 1)" gap note).
const GUJARAT_CENTER = [22.2587, 71.1924];

function markerColor(status) {
  if (status === "alert") return "#e02424";
  if (status === "route") return "#2563eb";
  if (status === "unhealthy") return "#9ca3af";
  return "#16a34a";
}

export default function MapView({ cameras, route, onSelectCamera, selectedCameraId }) {
  const located = useMemo(
    () => cameras.filter((c) => c.latitude != null && c.longitude != null),
    [cameras]
  );
  const routeLatLngs = useMemo(
    () =>
      (route || [])
        .filter((s) => s.latitude != null && s.longitude != null)
        .map((s) => [s.latitude, s.longitude]),
    [route]
  );

  const center = located.length
    ? [located[0].latitude, located[0].longitude]
    : routeLatLngs.length
    ? routeLatLngs[0]
    : GUJARAT_CENTER;

  return (
    <MapContainer center={center} zoom={routeLatLngs.length ? 12 : 7} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {located.map((cam) => (
        <CircleMarker
          key={cam.id}
          center={[cam.latitude, cam.longitude]}
          radius={cam.id === selectedCameraId ? 10 : 7}
          pathOptions={{
            color: markerColor(cam.live ? "healthy" : "unhealthy"),
            fillColor: markerColor(cam.live ? "healthy" : "unhealthy"),
            fillOpacity: 0.85,
          }}
          eventHandlers={{ click: () => onSelectCamera?.(cam.id) }}
        >
          <Popup>
            <strong>{cam.id}</strong>
            <br />
            {cam.location || "location unknown"}
            <br />
            {cam.live ? "live" : "offline"} · {cam.codec || "codec unknown"}
          </Popup>
        </CircleMarker>
      ))}
      {routeLatLngs.length > 1 && (
        <Polyline positions={routeLatLngs} pathOptions={{ color: markerColor("route"), weight: 3, dashArray: "6 6" }} />
      )}
      {(route || [])
        .filter((s) => s.latitude != null && s.longitude != null)
        .map((s, i) => (
          <CircleMarker
            key={`route-${i}`}
            center={[s.latitude, s.longitude]}
            radius={9}
            pathOptions={{ color: markerColor("route"), fillColor: "#fff", fillOpacity: 1, weight: 3 }}
          >
            <Popup>
              <strong>Stop {i + 1}</strong> — {s.camera_id}
              <br />
              {s.location || "location unknown"}
              <br />
              {new Date(s.observed_at).toLocaleString()}
            </Popup>
          </CircleMarker>
        ))}
    </MapContainer>
  );
}
