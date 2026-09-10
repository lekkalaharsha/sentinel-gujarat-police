import { useState } from "react";
import { api } from "../api";

// Model 1's "bulk import, API-based onboarding" + "manual onboarding demo"
// deliverables — this is the manual single-camera path (admin role
// required server-side, see routes_cameras.py's onboard_camera). Bulk
// import is the same endpoint's /cameras/bulk sibling, exercised via a
// script/CSV rather than a form for a 50-camera import.
const CAMERA_TYPES = ["", "fixed", "dome", "ptz", "bullet"];

export default function OnboardCameraForm({ onOnboarded }) {
  const [form, setForm] = useState({
    id: "", department: "", location_name: "", latitude: "", longitude: "",
    camera_type: "", is_restricted_zone: false, expected_direction_deg: "",
  });
  const [status, setStatus] = useState(null);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    if (!form.id) {
      setStatus({ error: "camera id is required" });
      return;
    }
    try {
      await api.onboardCamera({
        id: form.id.trim(),
        department: form.department.trim() || null,
        location_name: form.location_name.trim() || null,
        latitude: form.latitude ? Number(form.latitude) : null,
        longitude: form.longitude ? Number(form.longitude) : null,
        camera_type: form.camera_type || null,
        is_restricted_zone: form.is_restricted_zone,
        expected_direction_deg: form.expected_direction_deg !== "" ? Number(form.expected_direction_deg) : null,
      });
      setStatus({ ok: `onboarded ${form.id}` });
      setForm({
        id: "", department: "", location_name: "", latitude: "", longitude: "",
        camera_type: "", is_restricted_zone: false, expected_direction_deg: "",
      });
      onOnboarded?.();
    } catch (err) {
      setStatus({ error: err.message });
    }
  }

  return (
    <form onSubmit={submit} className="onboard-form">
      <h3>Onboard a camera</h3>
      <input placeholder="Camera ID (e.g. cam31)" value={form.id} onChange={(e) => set("id", e.target.value)} />
      <input placeholder="Department (e.g. Police)" value={form.department} onChange={(e) => set("department", e.target.value)} />
      <input placeholder="Location name" value={form.location_name} onChange={(e) => set("location_name", e.target.value)} />
      <div className="onboard-form__coords">
        <input placeholder="Latitude" value={form.latitude} onChange={(e) => set("latitude", e.target.value)} />
        <input placeholder="Longitude" value={form.longitude} onChange={(e) => set("longitude", e.target.value)} />
      </div>
      <select value={form.camera_type} onChange={(e) => set("camera_type", e.target.value)}>
        {CAMERA_TYPES.map((t) => (
          <option key={t} value={t}>{t ? t.toUpperCase() : "Camera type (optional)"}</option>
        ))}
      </select>
      <label className="onboard-form__checkbox">
        <input
          type="checkbox"
          checked={form.is_restricted_zone}
          onChange={(e) => set("is_restricted_zone", e.target.checked)}
        />
        Restricted zone (enables "stopped in zone" anomaly alerts)
      </label>
      <input
        placeholder="Expected direction of travel, degrees (optional, enables wrong-way alerts)"
        value={form.expected_direction_deg}
        onChange={(e) => set("expected_direction_deg", e.target.value)}
      />
      <button type="submit">Onboard</button>
      {status?.ok && <p className="onboard-form__ok">{status.ok}</p>}
      {status?.error && <p className="onboard-form__error">{status.error}</p>}
    </form>
  );
}
