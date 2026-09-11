# Model 1 — Requirements Coverage

Every bullet below is copied from the official challenge problem
statement's Model 1 section, then marked against real, verified code —
not a self-assessment from memory. First verified 2026-09-10; **all four
🟡 partials from that pass were closed the same day** in
`3306db6` (ageing tracking, coverage-radius layer, search filters,
onboarding audit trail) — re-verified against the diff and
`REQUIREMENTS_COVERAGE.md` 2026-09-11.

## Key functional features

| Requirement | Status | Evidence |
|---|---|---|
| Bulk import, manual entry, API-based onboarding | ✅ **Built** | `POST /cameras` (manual/API), `POST /cameras/bulk`, `OnboardCameraForm.jsx`, `scripts/onboard_from_catalogue.py` — see `REGISTRY_API.md` |
| Interactive GIS map with department/type/status/coverage layers | ✅ **Done 2026-09-10** | `MapView.jsx` now also renders a coverage-radius `Circle` per camera (`CameraRegistry.coverage_radius_m`) and a dashed-outline ageing flag, alongside the existing live/health color layer — closes the literal "layers" plural |
| Camera health and maintenance-status monitoring | 🟡 **Partial** (unchanged) | `is_healthy`/`last_seen_live_at` are real, backed by a live RTSP-worker health-sync loop — still no "maintenance status" concept beyond healthy/unhealthy/unknown (no AMC ticket, no scheduled-maintenance field). Not touched by `3306db6`; still an open gap, see `IMPLEMENTATION_PLAN.md`. |
| Gap-analysis reports for uncovered zones and ageing infra | ✅ **Done 2026-09-10** | `GET /cameras/gap-analysis` (+ `/export.pdf`) now reports `ageing`/`missing_install_date` alongside the existing catalogue-drift/missing-department/missing-GPS/unhealthy categories, backed by the new `CameraRegistry.install_date` column and `SENTINEL_CAMERA_AGEING_THRESHOLD_YEARS` (default 5) |
| Role-based search, filtering, export, metadata audit trails | ✅ **Done 2026-09-10** | RBAC + department-scoping (unchanged, already real); **backend search/filter query params** now live (`GET /cameras?department=&camera_type=&is_healthy=&live=&q=`); **onboarding audit trail** now real (`CameraAuditLog` table, admin-only `GET /cameras/{id}/audit-log`, records onboard vs. update per camera with an `id DESC` tiebreak for same-timestamp edits) |

## Expected deliverables

| Deliverable | Status | Evidence |
|---|---|---|
| Working registry portal with GIS map view | ✅ **Built** | `LiveMapView.jsx` + `MapView.jsx` + `CameraList.jsx`, live against real onboarded data |
| Bulk and manual camera-onboarding demonstration | ✅ **Built** | `POST /cameras`, `POST /cameras/bulk`, `OnboardCameraForm.jsx`, `onboard_from_catalogue.py` |
| Sample onboarded camera-metadata dataset | ✅ **Closed 2026-09-10** | `samples/cameras_export_2026-09-10.csv` — real 30-camera export, generated and checked in as part of this module pass (previously only existed as live DB rows, no static artifact) |
| Registry API documentation | ✅ **Closed 2026-09-10** | `REGISTRY_API.md` — previously only FastAPI's auto-generated `/docs`, no written reference existed |
| Sample gap-analysis report | ✅ **Closed 2026-09-10** | `samples/gap_analysis_report_2026-09-10.json` + `.md` — real captured output, previously only demoable live in the UI with no exported artifact |

## What's still honestly open

Only one 🟡 remains: **maintenance-status** beyond a binary healthy/
unhealthy flag (no AMC-ticket or scheduled-maintenance field). It doesn't
block the mandatory live technical-evaluation test case (cross-camera
vehicle tracking, watchlist alerts, GIS visualization of movement) — it's
a Model 1 completeness item, not a submission blocker. Everything else
that was 🟡 at the 2026-09-10 pass is now ✅ and covered by
`tests/test_camera_registry_model1.py` (backend suite 53/53 passing at
the time of that commit).
