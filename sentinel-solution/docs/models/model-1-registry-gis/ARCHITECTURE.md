# Model 1 — Centralised CCTV Registry & GIS Mapping — Architecture

Ground-truthed 2026-09-10 against the real, running Sentinel backend/
frontend (not a proposal — this model is built and demoable today).

## Where Model 1 sits

Sentinel is submitted as a **Model 1 + Model 2 hybrid**. Model 1 is the
foundational layer: it owns camera *metadata* (identity, location,
department, health) and never touches live video itself — that's Model
2's job (`sentinel-solution/docs/models/model-2-unified-viewing/`). The
two share one database and one FastAPI process in this pilot, but are
logically separable: Model 1's `CameraRegistry` table and `/cameras/*`
endpoints would function even with the Model 2 streaming/analytics layer
entirely removed.

## Component diagram

```text
┌─────────────────────────────────────────────────────────────────┐
│ Onboarding sources                                               │
│  - Manual entry (OnboardCameraForm.jsx)                          │
│  - Bulk CSV/script (scripts/onboard_from_catalogue.py)           │
│  - API-based (POST /cameras, POST /cameras/bulk)                 │
└───────────────────────────┬───────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ CameraRegistry (SQLAlchemy model, db/models.py)                  │
│  id, department, location_name, lat/lon, vendor, camera_type,    │
│  is_restricted_zone, expected_direction_deg, is_healthy,         │
│  last_seen_live_at                                               │
│  — table name: camera_registry (singular snake_case)             │
└───────────────────────────┬───────────────────────────────────────┘
                            │  health-sync loop (main.py, every        
                            │  CATALOGUE_REFRESH_INTERVAL_S) reconciles 
                            │  against StreamManager's live RTSP worker 
                            │  state — auto-creates a bare registry row  
                            │  for any active worker not yet onboarded  
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ FastAPI routes_cameras.py — role + department-scoped              │
│  GET  /cameras                (list, merged w/ live health)       │
│  GET  /cameras/{id}                                                │
│  GET  /cameras/gap-analysis    (investigator+)                    │
│  GET  /cameras/export.csv      (investigator+, no credential cols) │
│  POST /cameras, /cameras/bulk  (admin, upsert semantics)           │
└───────────────────────────┬───────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Frontend                                                          │
│  - MapView.jsx / LiveMapView.jsx — Leaflet GIS view,               │
│    pins colored by live/health status                             │
│  - CameraList.jsx — list + health dot                              │
│  - GapAnalysisPanel.jsx — live gap-analysis rendering              │
│  - OnboardCameraForm.jsx — manual onboarding UI                    │
└─────────────────────────────────────────────────────────────────┘
```

## Data flow: from an unknown camera to a registered, mapped one

1. A camera appears in the sandbox catalogue (`CatalogueClient.refresh()`)
   and/or a RTSP worker connects to it (`StreamManager`).
2. `main.py`'s health-sync loop notices an active worker with no
   `CameraRegistry` row and auto-creates a bare one — so a camera is
   never "invisible" to the registry even before anyone runs onboarding.
3. `scripts/onboard_from_catalogue.py` (or manual/bulk API calls) fills
   in department/location/GPS metadata via upsert — re-running it is
   safe and expected as data quality improves.
4. `GET /cameras` merges registry rows with live health state
   (`is_healthy`, `last_seen_live_at`) computed by the reconcile loop —
   never a stale snapshot.
5. The frontend's `MapView.jsx` renders every camera as a pin, colored by
   current live/health status; `GapAnalysisPanel.jsx` and
   `CameraList.jsx` surface the same merged data differently.
6. `GET /cameras/gap-analysis` computes six deltas (catalogue-vs-registry
   drift, missing department, missing GPS, unhealthy) purely from
   already-collected data — no separate ingestion path.

## Deviation from the suggested stack (and why)

| Suggested | Actual | Why |
|---|---|---|
| PostgreSQL + PostGIS | SQLite | Pilot scale (30 cameras); `DATABASE_URL` is env-swappable to PostgreSQL with zero code change per `SCALABILITY.md`'s district-tier step — this is a deliberate, documented scale decision, not an oversight. |
| Node.js or Python (Django/FastAPI) | Python/FastAPI | Matches the suggestion directly. |
| Leaflet / OpenLayers | Leaflet (`react-leaflet`) | Matches the suggestion directly. |
| Department-wise RBAC | Real, enforced (`department_scope()`) | Matches the suggestion directly — verified applied to `list_cameras`, `gap_analysis`, `get_camera`, `export_cameras_csv`. |

No PostGIS-specific spatial query (radius search, polygon coverage) is
implemented — coordinates are stored as plain float columns, queried by
equality/nullness only. This is the one real architectural gap versus
the suggested stack; see `IMPLEMENTATION_PLAN.md`.
