# Camera Registry API Reference (Model 1)

Closes a previously-open gap: this repo had no written API reference for
the registry endpoints, only FastAPI's auto-generated OpenAPI UI at
`/docs`. This file is the human-readable equivalent, verified directly
against `sentinel-solution/backend/app/api/routes_cameras.py` (2026-09-10) —
every field name below is copied from the real Pydantic model / response
dict, not reconstructed from memory.

All endpoints require `X-Sentinel-API-Key` header auth. Roles are ranked
`viewer < investigator < admin`; a role satisfies any requirement at or
below it.

## `GET /cameras`
**Role:** `viewer`+. Department-scoped for non-admins (see `department_scope()`
in `api/auth.py` — a non-admin only sees their own department's cameras).
Returns the full merged view (registry metadata + live health/stream
info) for every camera the caller is allowed to see. `rtsp_url`/`whep_url`
are `null` unless the caller is `admin` (they embed real sandbox
`email:password@` credentials — see `_merged_camera_view()`).

## `GET /cameras/{camera_id}`
**Role:** `viewer`+. Single-camera version of the above.

## `GET /cameras/{camera_id}/last-detection`
**Role:** `viewer`+. Most recent sampled-frame analytics detection for one
camera (used by the frontend's per-camera detail view) — belongs
conceptually to Model 2 (analytics), listed here for completeness since
it hangs off the same router.

## `GET /cameras/gap-analysis`
**Role:** `investigator`+. Department-scoped. Response shape (exact,
verified 2026-09-10 against a live 30-camera catalogue):
```json
{
  "catalogue_size": 30,
  "registered_size": 30,
  "live_not_onboarded": ["cam_id", "..."],
  "onboarded_not_live": ["cam_id", "..."],
  "missing_department": ["cam_id", "..."],
  "missing_gis_coordinates": ["cam_id", "..."],
  "unhealthy": ["cam_id", "..."],
  "cameras_by_department": {"<dept-or-'unassigned'>": <count>, "...": "..."}
}
```
See `samples/gap_analysis_report_2026-09-10.json` for a real captured
example and `samples/gap_analysis_report_2026-09-10.md` for the
human-readable write-up.

## `GET /cameras/export.csv`
**Role:** `investigator`+. Department-scoped. Streams a CSV with columns
(exact, verified against a real export): `id, location, department,
vendor, camera_type, latitude, longitude, is_healthy, last_seen_live_at,
is_restricted_zone, expected_direction_deg, onboarded, live`. Admin-only
URL fields (`rtsp_url`/`whep_url`) are **never** included in this export,
for any role — the credential-leak risk is closed at the export layer,
not just the JSON endpoints. See `samples/cameras_export_2026-09-10.csv`
for a real captured example (30 cameras).

## `POST /cameras`
**Role:** `admin`. Manual/API-based single-camera onboarding — this is
the "manual entry" + "API-based onboarding" deliverable. **Upsert
semantics**: onboarding an already-known camera ID updates its metadata
rather than erroring (re-running a bulk import with corrected data is a
normal workflow here, not an edge case).

Request body (`CameraOnboard`, exact fields from `routes_cameras.py`):
```json
{
  "id": "cam31",
  "department": "Police",
  "location_name": "Example Junction",
  "latitude": 23.03,
  "longitude": 72.51,
  "vendor": "Hikvision",
  "camera_type": "PTZ",
  "is_restricted_zone": false,
  "expected_direction_deg": 90.0
}
```
Only `id` is required; every other field defaults to `null`/`false`.
Response: `{"status": "onboarded", "id": "cam31"}`.

## `POST /cameras/bulk`
**Role:** `admin`. This is the "bulk import" deliverable — a JSON array
of `CameraOnboard` objects (same schema as above), applied in one
transaction. Used by `scripts/onboard_from_catalogue.py` to bulk-onboard
the live sandbox catalogue with heuristically-inferred department/GIS
data. Response: `{"status": "onboarded", "count": <n>, "ids": ["cam01", "..."]}`.

## Known gaps (honest, not hidden — see `IMPLEMENTATION_PLAN.md`)
- No backend query-param filtering on `GET /cameras` (department/type/
  status filters are client-side only in the frontend today).
- No camera-onboarding audit trail (who onboarded/edited which camera and
  when — `AuditLog` currently only covers vehicle-search queries).
- No install-date/equipment-age field, so "ageing infrastructure" can't
  be computed by `/cameras/gap-analysis` yet.
