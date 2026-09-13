# Task for Codex — add a bulk camera-import GUI (CSV upload/paste)

Read `CLAUDE.md` at the repo root (and `sentinel-solution`'s if present)
first and follow it — especially the honesty rules (§24.5), minimal-diff
rule (§24.1), and git rules (§19/§25: do not commit/push, only edit the
working tree).

## Why

Model 1's mandatory spec (`docs/hackathon/HACKATHON_DETAILS.md` §7)
literally names **"bulk/manual onboarding demo"** as a deliverable. An
audit of the current frontend found manual onboarding is real and in the
GUI (`OnboardCameraForm.jsx`), but bulk import is **backend-only** — the
endpoint (`POST /cameras/bulk` in `routes_cameras.py`) exists and is
already exercised by `onboard_cameras_bulk`/tests, but there is no
frontend caller at all: no entry in `api.js`, no UI, not even a script
someone could point a demo camera at. This is the one real gap against
that named deliverable — everything else in Model 1 (manual onboarding,
GIS map, health monitoring, gap-analysis, RBAC) already has a working
GUI. Close it.

## What to build

A bulk-import panel, placed in the same screen as the existing manual
onboarding form (`CameraNetworkView.jsx`, alongside
`<OnboardCameraForm onOnboarded={onOnboarded} />` — put the new component
next to it in the same `cols2` row or directly below, your call on
layout, but keep it on this screen, not a new nav page).

Backend contract already exists — reuse it exactly, do not change it:

```
POST /cameras/bulk
body: [ { id, department?, location_name?, latitude?, longitude?,
          vendor?, camera_type?, is_restricted_zone?,
          expected_direction_deg?, install_date?, coverage_radius_m? }, ... ]
-> { status: "onboarded", count: N, ids: [...] }
```
(admin-only — `require_role("admin")`, same as the single-camera path;
see `routes_cameras.py`'s `onboard_cameras_bulk`.) `CameraOnboard`
(pydantic model, same file) is the authoritative field list — match it
exactly, don't invent extra fields.

Frontend:
1. **`api.js`**: add `onboardCamerasBulk: (cameras) => request("/cameras/bulk", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(cameras) })` — mirror `onboardCamera`'s existing shape exactly, don't reinvent the request helper.
2. **New component** (e.g. `BulkOnboardForm.jsx`):
   - A `<textarea>` where an admin pastes CSV rows (header row required:
     `id,department,location_name,latitude,longitude,vendor,camera_type,is_restricted_zone,expected_direction_deg,install_date,coverage_radius_m`
     — `id` is the only required column, everything else optional/blank
     allowed, matching `CameraOnboard`'s own nullability) — **and** a
     native `<input type="file" accept=".csv">` that reads a chosen file
     into the same textarea via `FileReader`, so both "paste" and
     "upload a file" work through one parser. Do not add a server-side
     upload endpoint — parse client-side and send normal JSON to the
     existing `/cameras/bulk` endpoint, exactly like the file-shaped
     parsing this repo already uses elsewhere for CSV-ish flows (check
     `export_cameras_csv` in `routes_cameras.py` for the column order
     convention to stay consistent with).
   - Parse rows into the `CameraOnboard` shape (empty string -> `null`,
     numeric fields -> `Number(...)` or `null`, `is_restricted_zone` ->
     boolean from `"true"/"1"` etc. — same coercion style
     `OnboardCameraForm.jsx` already uses for its single-row equivalent,
     reuse that logic rather than writing a parallel version if you can
     factor it into a small shared helper).
   - **Validate before sending**: reject rows with no `id`, reject
     duplicate `id`s within the pasted batch, show a clear per-row error
     list rather than silently dropping bad rows or sending garbage to
     the backend. Show a preview table (row count, first few rows) before
     the admin confirms submission — don't submit on every keystroke.
   - On submit, call the new `api.onboardCamerasBulk(...)`, show the
     real `count`/`ids` the backend returned (not the count you parsed
     client-side — if the backend silently deduped or partially failed,
     the real response is the truth), and call the existing `onOnboarded`
     callback (same prop `OnboardCameraForm` already receives) so the
     camera list refreshes.
   - Provide a **"Download CSV template"** link/button (a static
     client-side blob with just the header row + one example line) so an
     admin without existing data still has a starting point — this is
     the practical version of the spec's "sample metadata dataset"
     deliverable for this path.
3. Wire the new component into `CameraNetworkView.jsx` next to
   `OnboardCameraForm`, passing the same `onOnboarded` prop through.
4. Keep this admin-gated in spirit even though the backend already
   enforces it server-side (a non-admin key gets a real 403) — no need
   to hide the UI element itself (that's fine, other forms in this repo
   don't hide by role either — check `OnboardCameraForm.jsx`'s
   convention and match it, don't invent a new client-side gating
   pattern for just this one form).

## Constraints (from this repo's CLAUDE.md — follow exactly)

- No fabricated data: the "download template" CSV must contain one
  clearly-fake, obviously-example row (e.g. id `cam-example-01`), never
  something that could be mistaken for a real onboarded camera.
- Don't touch `routes_cameras.py`'s `POST /cameras/bulk` contract or
  `CameraOnboard` — this is a frontend-only task. If you find a real bug
  in the existing bulk endpoint while testing against it, report it,
  don't silently patch unrelated backend behavior as part of this task.
- Minimal diff: reuse `api.js`'s existing `request()` helper and
  `OnboardCameraForm.jsx`'s row-to-`CameraOnboard` coercion logic instead
  of duplicating it from scratch — factor out a small shared function if
  that keeps both forms in sync, rather than two copies that can drift.
- Don't introduce a CSV-parsing library dependency for this — the format
  is simple (comma-separated, no embedded commas/quotes expected in
  practice for this dataset) and this repo's dependency policy (§24.13)
  requires justifying any new dependency; a small hand-rolled parser is
  fine and is what the rest of this repo does for CSV (see
  `export_cameras_csv`/`csv` module usage patterns already in the repo —
  actually check whether the *frontend* already parses CSV anywhere
  before deciding hand-rolled vs using the browser's built-in
  `String.split` approach; keep it simple either way).
- Test what you add: this repo doesn't appear to have frontend unit
  tests (check first — if there's a test runner already configured,
  use it; if not, don't introduce one just for this). At minimum: run
  `npm run lint` and `npm run build` in `sentinel-solution/frontend` —
  both must be clean/passing. Then **actually exercise it**: start the
  backend (`sentinel-solution/backend`, `.venv/Scripts/python.exe -m
  app.main`) and frontend (`npm run dev`), mint or use an admin key, and
  really paste a small multi-row CSV through the new form against the
  live backend — confirm the real camera count increases and the new
  cameras show up in the existing camera list/map. Report what you
  actually ran and saw, not just that the build passed.
- Do not commit, push, or open a PR. Leave the changes in the working
  tree. At the end, report: what changed, files touched, whether you
  found and reused `OnboardCameraForm.jsx`'s existing coercion logic
  or wrote new logic (and why), lint/build results, and the real
  end-to-end check you ran against the live backend.
