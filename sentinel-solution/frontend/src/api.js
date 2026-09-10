const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const API_KEY_STORAGE_KEY = "sentinel_api_key";

export function getApiKey() {
  return localStorage.getItem(API_KEY_STORAGE_KEY) || "";
}

export function setApiKey(key) {
  if (key) localStorage.setItem(API_KEY_STORAGE_KEY, key);
  else localStorage.removeItem(API_KEY_STORAGE_KEY);
}

async function request(path, options = {}) {
  const apiKey = getApiKey();
  const headers = { ...(options.headers || {}) };
  if (apiKey) headers["X-Sentinel-API-Key"] = apiKey;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail;
    try {
      detail = (await res.json()).detail;
    } catch {
      detail = res.statusText;
    }
    if (res.status === 401) throw new Error("401 missing/invalid API key — set one above");
    if (res.status === 403) throw new Error(`403 your role can't do this (${detail || "insufficient permissions"})`);
    throw new Error(`${res.status} ${detail || ""}`.trim());
  }
  return res.json();
}

export const api = {
  base: API_BASE,
  health: () => request("/health"),
  whoami: () => request("/auth/whoami"),
  listCameras: () => request("/cameras"),
  getCamera: (id) => request(`/cameras/${id}`),
  gapAnalysis: () => request("/cameras/gap-analysis"),
  onboardCamera: (camera) =>
    request("/cameras", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(camera),
    }),
  vehicleHistory: (plate, purpose, caseId) => {
    const params = new URLSearchParams({ purpose });
    if (caseId) params.set("case_id", caseId);
    return request(`/vehicle/${encodeURIComponent(plate)}/history?${params}`);
  },
  searchByAttributes: (purpose, { vehicleType, color, partialPlate, caseId } = {}) => {
    const params = new URLSearchParams({ purpose });
    if (vehicleType) params.set("vehicle_type", vehicleType);
    if (color) params.set("color", color);
    if (partialPlate) params.set("partial_plate", partialPlate);
    if (caseId) params.set("case_id", caseId);
    return request(`/vehicle/search-by-attributes?${params}`);
  },
  listWatchlist: () => request("/watchlist"),
  addWatchlist: (plate, reason) =>
    request("/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plate, reason }),
    }),
  listAlerts: (limit = 100) => request(`/alerts?limit=${limit}`),
  ackAlert: (id) => request(`/alerts/${id}/ack`, { method: "POST" }),
  setAlertStatus: (id, status) =>
    request(`/alerts/${id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }),
  hlsUrl: (cameraId) => `${API_BASE}/live/${cameraId}/index.m3u8`,

  candidateCameras: (plate, purpose, caseId) => {
    const params = new URLSearchParams({ purpose });
    if (caseId) params.set("case_id", caseId);
    return request(`/vehicle/${encodeURIComponent(plate)}/candidate-cameras?${params}`);
  },
  lastDetection: (cameraId) => request(`/cameras/${cameraId}/last-detection`),
  eventCropUrl: (eventId) => `${API_BASE}/vehicle/event/${eventId}/crop`,
  // Auth'd image fetch — API key is a header, not a query param, so an
  // <img src> can't carry it. Fetch as a blob and hand back an object URL.
  eventCropBlobUrl: async (eventId) => {
    const apiKey = getApiKey();
    const res = await fetch(`${API_BASE}/vehicle/event/${eventId}/crop`, {
      headers: apiKey ? { "X-Sentinel-API-Key": apiKey } : {},
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return URL.createObjectURL(await res.blob());
  },
  auditLog: (limit = 200) => request(`/admin/audit-log?limit=${limit}`),
  retentionPolicy: () => request("/admin/retention-policy"),
  triggerPurge: () => request("/admin/purge", { method: "POST" }),
  recentDetections: (limit = 20) => request(`/vehicle/recent?limit=${limit}`),
};
