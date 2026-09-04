function healthClass(cam) {
  if (cam.is_healthy === true) return "camera-list__dot--live";
  if (cam.is_healthy === false) return "camera-list__dot--offline";
  return "camera-list__dot--unknown"; // never confirmed live — see models.py's is_healthy comment
}

export default function CameraList({ cameras, selectedCameraId, onSelectCamera }) {
  return (
    <div className="camera-list">
      <h3>Camera registry ({cameras.length})</h3>
      <ul>
        {cameras.map((cam) => (
          <li
            key={cam.id}
            className={`camera-list__item ${cam.id === selectedCameraId ? "camera-list__item--selected" : ""}`}
            onClick={() => onSelectCamera(cam.id)}
          >
            <span className={`camera-list__dot ${healthClass(cam)}`} title={cam.is_healthy === null ? "health unknown — never confirmed live" : undefined} />
            <span className="camera-list__id">{cam.id}</span>
            <span className="camera-list__location">{cam.location || "unknown location"}</span>
            {cam.department && <span className="camera-list__department">{cam.department}</span>}
          </li>
        ))}
        {!cameras.length && <li className="camera-list__empty">No cameras onboarded yet.</li>}
      </ul>
    </div>
  );
}
