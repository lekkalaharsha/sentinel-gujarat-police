# Task for Codex — merge Live Map + Video Wall + camera detail drill-down into one "Live Network" screen

Read `CLAUDE.md` at the repo root first (both the top-level one and
`sentinel-solution`'s if present) and follow it — especially the honesty
rules (§24.5, §24.11), the minimal-diff rule (§24.1), and the git rules
(§19/§25: do not commit/push, only edit the working tree).

## Goal

Today the sidebar has two separate pages that should really be one
operational screen:

- `LiveMapView.jsx` (nav id `"livemap"`) — full statewide GIS map.
- `CameraGridView.jsx` (nav id `"grid"`) — video wall, currently caps at
  9 simultaneous HLS tiles (`MAX_TILES = 9` in `CameraGridView.jsx`).

Merge them into a single screen (keep the file name `LiveMapView.jsx` and
nav id `"livemap"` — do not introduce a third page/nav id) with this
layout, top to bottom:

1. **Filter bar** — Department filter (real data, see "Data reality
   check" below), State is fixed to Gujarat (no picker needed).
2. **Map** — same `MapView` component already used here, now filtered by
   the selected department. Clicking a camera pin selects it.
3. **Video wall** — below or beside the map. Only cameras that pass the
   current filter are selectable as tiles. Cap tile count to a toggle of
   **4 or 6, never more** (replace `CameraGridView`'s existing "First 4" /
   "First 9" buttons with "4" / "6", and clamp `MAX_TILES` to 6).
4. **Info icon per tile** — every video-wall tile (both live HLS tiles
   and the existing external-snapshot tiles from `SnapshotView.jsx`) gets
   a small (ℹ) icon overlay, top-right corner, that opens a detail
   panel/modal for that camera (see "Camera detail panel" below). Do not
   remove the existing tile label; add the icon alongside it.

Reuse `CameraGridView`'s existing tile-selection state/logic and
`SnapshotView` integration rather than rewriting it — move/adapt that
code into the merged component, don't duplicate it. Once merged, retire
`CameraGridView.jsx` and remove the `"grid"` nav entry from `Sidebar.jsx`
and its case in `App.jsx` — one screen, not two with overlapping purpose.

## Data reality check — do not fabricate district/region

`CameraRegistry` (`sentinel-solution/backend/app/db/models.py`) has no
`district` or `region` column — only `department`, `latitude`,
`longitude`. `StatewideOverview.jsx` already documents this explicitly:
*"This pilot's registry has no district-level metadata yet... a real
production registry would add one rather than have this UI invent
statewide locations that don't exist."* Respect that precedent:

- **Department filter**: real, build it — `department` is a genuine
  column with real onboarded values (5 real Gujarat departments +
  "Unassigned" + the new `"External — Caltrans District 3..."` value
  from the Model 2 two-system feature — decide whether external cameras
  should appear in this department dropdown at all, or get their own
  "External sources" filter bucket; either is fine, just don't silently
  drop them or silently merge them into a fake Gujarat department).
- **District filter**: **do not add a district picker that has nothing
  real to filter by.** If you want a district tier, it needs a real
  `district` column on `CameraRegistry` (additive migration, nullable,
  populated only where a human/onboarding source actually provides it —
  same pattern as `install_date`/`coverage_radius_m`). That is a schema
  change — **stop and ask before adding it**, don't do it silently
  as part of this UI task. Default assumption for this task: **skip
  district**, filter on department only, and say so in your summary
  rather than quietly working around it.
- **Region**: if you want a coarser-than-department grouping, the only
  honest option with current data is a GIS-derived cluster from
  lat/lon (e.g. simple geographic bucketing) — and it MUST be labelled
  in the UI as derived/approximate, never presented as an official
  administrative region. If this feels like scope creep for this task,
  skip it and say so — department-only filtering is an acceptable, honest
  deliverable on its own.

## Camera detail panel (the info-icon click target)

Backend currently has, per camera:
- `GET /cameras/{id}` — registry metadata (already used).
- `GET /cameras/{id}/last-detection` — single most recent event only
  (`routes_cameras.py`).

It does **not** currently have a camera-scoped list of recent events, a
per-camera vehicle count, or a camera-scoped alerts filter. `GET
/vehicle/recent` (`routes_vehicle.py`) and `GET /alerts`
(`routes_alerts.py`) both exist but have no `camera_id` query param.

Add what's actually needed, following existing patterns exactly (same
file, same RBAC decorators, same department-scope pattern used
everywhere else in these two files — do not weaken or bypass
`department_scope`/`require_role`):

- Add an optional `camera_id: str | None = None` query param to
  `GET /vehicle/recent`, filtering `VehicleEvent.camera_id == camera_id`
  when set. Reuse the existing serialization — don't build a parallel one.
- Add an optional `camera_id: str | None = None` query param to
  `GET /alerts`, filtering `Alert.camera_id == camera_id` when set,
  composed with the existing department-scope filter (not replacing it).
- Add a small aggregate, e.g. `GET /cameras/{id}/stats` (or fold into the
  existing `GET /cameras/{id}` response — your call) returning at least:
  a vehicle-sighting count for a bounded recent window (e.g. last 24h —
  pick a real, disclosed window, don't claim "total" if you're actually
  capping the query), and the count broken out by whether each sighting
  is `CONFIRMED`/`PROBABLE`/`LEAD_ONLY` (reuse `evidence_class.py`'s
  existing classifier — do not invent a new confidence scheme). Keep the
  underlying query bounded (`LIMIT`/date-range), not a full table scan —
  this endpoint will be hit whenever the info icon opens.

Frontend detail panel, once opened for a camera, should show:
- Registry basics already available from `GET /cameras/{id}`
  (department, location, health, ANPR suitability if present).
- Last real detection (`GET /cameras/{id}/last-detection`): plate,
  plate confidence, vehicle type, color, evidence crop thumbnail if
  `has_evidence_image`.
- Recent sightings list + count for this camera (from the new
  `camera_id`-filtered `/vehicle/recent` call and/or the new stats
  endpoint) — show evidence-tier per row (CONFIRMED/PROBABLE/LEAD_ONLY),
  visually distinct per this repo's existing tier-color convention
  (check `StatusTag.jsx`/existing evidence-tier styling and reuse it,
  don't invent new colors).
- Any watchlist alert(s) tied to this camera (from the new
  `camera_id`-filtered `/alerts` call): reason, alert_type, status. If
  there are none, say "No active alerts for this camera" — don't hide
  the section or show a misleading empty state.
- For an external/snapshot-only camera (`source_system` set,
  `snapshot_image_url` present): no vehicle/plate/alert data will exist
  (no analytics run on these) — the panel must say so plainly ("No
  analytics run on this external source") rather than showing a
  confusing empty vehicle list that looks like a bug.

## Constraints (carried over from this repo's CLAUDE.md — follow exactly)

- No fabricated data anywhere — every number in the new panel must trace
  to a real query. If something can't be computed honestly from current
  data, omit it and say so in your summary rather than approximating it
  silently.
- LEAD_ONLY sightings shown in the detail panel must stay visually
  distinct from CONFIRMED/PROBABLE and must not be exportable as
  evidence from this panel (don't add an export button here at all
  unless asked).
- Any DB schema change (only relevant if you decide to add `district`)
  must be an additive, nullable migration in
  `sentinel-solution/backend/app/db/session.py`'s `_ADDITIVE_MIGRATIONS`
  list, following the existing pattern exactly — and per above, ask
  first rather than doing this silently.
- RBAC: new/modified endpoints keep the same role requirements and
  department-scoping as their neighbors in the same file — a
  department-scoped investigator must not be able to see another
  department's camera detail via the new endpoints.
- Preserve existing API contracts: don't rename/remove existing response
  fields on `/cameras`, `/vehicle/recent`, or `/alerts` — only add.
- Minimal diff: reuse `MapView`, `SnapshotView`, `LiveView`,
  `StatusTag`, and the existing evidence-tier styling rather than
  rewriting any of them. Don't touch unrelated views.
- Test what you add: backend — new `camera_id` filter behavior and the
  new stats endpoint, using this repo's existing pytest fixtures/patterns
  (see `tests/test_external_camera_source.py` or any `routes_*` test for
  the house style). Frontend — run `npm run lint` and `npm run build` in
  `sentinel-solution/frontend`; both must be clean/passing. Backend — run
  `.venv/Scripts/python.exe -m pytest tests -v` in
  `sentinel-solution/backend`; report the pass count.
- Do not commit, push, or open a PR. Leave the changes in the working
  tree. At the end, report: what changed, files touched, tests actually
  run and their results, any endpoint/contract changes, and — explicitly
  — whether you added a real district/region concept or skipped it (and
  why), since that's the one place in this task where fabricating data
  would be an easy trap.
