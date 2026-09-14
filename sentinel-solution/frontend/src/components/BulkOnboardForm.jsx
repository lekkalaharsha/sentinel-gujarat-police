import { useMemo, useState } from "react";
import { api } from "../api";

const HEADERS = ["id", "department", "location_name", "latitude", "longitude", "vendor", "camera_type", "is_restricted_zone", "expected_direction_deg", "install_date", "coverage_radius_m"];
const SAMPLE = `${HEADERS.join(",")}\ncam-example-01,Example department,Example location,22.2587,71.1924,Example vendor,fixed,false,,,`;

function value(row, key) { return row[key]?.trim() || null; }
function parseCsv(text) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (!lines.length) return { rows: [], errors: ["Add a header row and at least one camera row."] };
  const headers = lines[0].split(",").map((item) => item.trim());
  const missing = HEADERS.filter((header) => !headers.includes(header));
  if (missing.length) return { rows: [], errors: [`Missing required columns: ${missing.join(", ")}`] };
  const ids = new Set(); const errors = []; const rows = [];
  lines.slice(1).forEach((line, index) => {
    const cells = line.split(","); const raw = Object.fromEntries(headers.map((header, i) => [header, cells[i] || ""]));
    const id = value(raw, "id");
    if (!id) { errors.push(`Row ${index + 2}: id is required`); return; }
    if (ids.has(id)) { errors.push(`Row ${index + 2}: duplicate id ${id}`); return; }
    ids.add(id);
    const number = (key) => value(raw, key) == null ? null : Number(raw[key]);
    const numericFields = ["latitude", "longitude", "expected_direction_deg", "coverage_radius_m"];
    const invalidNumber = numericFields.find((key) => value(raw, key) != null && !Number.isFinite(number(key)));
    if (invalidNumber) { errors.push(`Row ${index + 2}: ${invalidNumber} must be numeric`); return; }
    const bool = value(raw, "is_restricted_zone");
    rows.push({ id, department: value(raw, "department"), location_name: value(raw, "location_name"), latitude: number("latitude"), longitude: number("longitude"), vendor: value(raw, "vendor"), camera_type: value(raw, "camera_type"), is_restricted_zone: bool === null ? false : ["true", "1", "yes"].includes(bool.toLowerCase()), expected_direction_deg: number("expected_direction_deg"), install_date: value(raw, "install_date"), coverage_radius_m: number("coverage_radius_m") });
  });
  return { rows, errors };
}

export default function BulkOnboardForm({ onOnboarded }) {
  const [text, setText] = useState(""); const [status, setStatus] = useState(null); const [loading, setLoading] = useState(false);
  const parsed = useMemo(() => parseCsv(text), [text]);
  function downloadTemplate() { const url = URL.createObjectURL(new Blob([SAMPLE], { type: "text/csv" })); const a = document.createElement("a"); a.href = url; a.download = "camera-onboarding-template.csv"; a.click(); URL.revokeObjectURL(url); }
  async function submit(event) { event.preventDefault(); setStatus(null); if (parsed.errors.length || !parsed.rows.length) { setStatus({ error: "Fix the CSV errors before submitting." }); return; } setLoading(true); try { const result = await api.onboardCamerasBulk(parsed.rows); setStatus({ ok: `Backend onboarded ${result.count} camera(s): ${(result.ids || []).join(", ")}` }); setText(""); onOnboarded?.(); } catch (error) { setStatus({ error: error.message }); } finally { setLoading(false); } }
  return <form className="onboard-form bulk-onboard-form" onSubmit={submit}>
    <div className="bulk-onboard-form__title"><div><h3>Bulk import cameras</h3><p className="sub">Admin-only CSV import using the existing camera catalogue contract.</p></div><button type="button" className="btn2" onClick={downloadTemplate}>Download CSV template</button></div>
    <input type="file" accept=".csv,text/csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = () => setText(String(reader.result || "")); reader.readAsText(file); } }} />
    <textarea rows="6" value={text} onChange={(event) => setText(event.target.value)} placeholder={HEADERS.join(",")} />
    {text && <div className="bulk-onboard-preview"><strong>Preview · {parsed.rows.length} valid row(s)</strong>{parsed.errors.map((error) => <div key={error} className="onboard-form__error">{error}</div>)}{parsed.rows.slice(0, 4).map((row) => <div key={row.id} className="sub">{row.id} · {row.department || "Unassigned"} · {row.location_name || "Location unknown"}</div>)}</div>}
    <button type="submit" disabled={loading}>{loading ? "Importing…" : "Import cameras"}</button>
    {status?.ok && <p className="onboard-form__ok">{status.ok}</p>}{status?.error && <p className="onboard-form__error">{status.error}</p>}
  </form>;
}
