# Task for Codex — disclose evidence-tier and non-dedup on the Attribute Search screen

Read `CLAUDE.md` at the repo root (and `sentinel-solution`'s if present)
first and follow it — especially the honesty rules (§24.5, §24.11,
"Confidence-tier enforcement" §6 Priority D), and the minimal-diff rule
(§24.1). Do not commit/push — leave changes in the working tree.

## Why

Audited `SearchView.jsx` (Attribute Search — `GET
/vehicle/search-by-attributes`) against `VehicleTimeline.jsx` (Vehicle
Search's plate-history view) and found a real gap: `VehicleTimeline.jsx`
shows a CONFIRMED/PROBABLE/LEAD_ONLY tier badge on every sighting
(`analytics/evidence_class.py`'s classifier, backend-computed, never
re-derived client-side per that file's own docstring). `SearchView.jsx`
shows none of that — its results table just lists camera/time/plate/
type-color with no evidence-tier indication at all.

This matters because attribute search has a real, disclosed limitation
that isn't currently disclosed **in the UI**: `search_by_attributes` in
`routes_vehicle.py` returns a flat list of raw `VehicleEvent` rows
matching color/type/partial-plate — it does NOT cluster or deduplicate
into distinct vehicles, and any row whose plate came from appearance-only
linking has the same known weakness as the rest of this system's
appearance signal (41.87% measured false-positive rate,
`DECISION_REVIEW_2026-09-11.md`). An investigator looking at this table
today has no on-screen signal that two similar-looking rows might be two
different real cars, or that an "anonymous" row's presence in these
results doesn't mean it's confirmed to match the filters as strongly as
a plate-read row does.

## What to add

**1. Backend — `routes_vehicle.py`'s `search_by_attributes`:**
Add `evidence_class` (and `evidence_class_reason`) to each row in the
response, reusing the exact same `_cls(e)` helper (defined earlier in
this file, already used by `/vehicle/recent` and
`/vehicle/{plate}/history` — do not write a second implementation) and
`ec.describe(...)`/`ec.is_exportable(...)` from `analytics/evidence_class`
(already imported in this file as `ec`). This is additive to the
response shape — don't remove or rename any existing field
(`camera_id`, `location`, `observed_at`, `plate`, `plate_confidence`,
`vehicle_type`, `color` all stay as-is).

**2. Frontend — `SearchView.jsx`:**
- Add an **Evidence tier** column to the results table, rendering the
  same tier badge component `VehicleTimeline.jsx` already defines
  (`TierBadge`, currently a private, non-exported function in that
  file — **export it from `VehicleTimeline.jsx` and import it here**
  rather than copy-pasting the `TIER` map/styling into a second file;
  keep the two screens' badges visually identical and in sync, since
  they're describing the same backend concept).
- Add a one-line disclosure banner above the results table (only shown
  when `result.matches.length > 0`), something like: *"These are
  individual sightings, not deduplicated vehicles — two rows can be two
  different real vehicles that share these attributes. LEAD ONLY rows
  are appearance-based leads, not confirmed matches."* Match this
  repo's existing banner/note styling (check how `result.truncated`'s
  warning is styled just above where you're adding this, in the same
  file, and stay consistent rather than inventing new inline styles).
- LEAD_ONLY rows must not visually look the same as CONFIRMED/PROBABLE
  rows — reuse whatever visual distinction `VehicleTimeline.jsx` already
  uses for this (border/background/opacity — check its rendering) rather
  than inventing a new convention here.

## Constraints (from this repo's CLAUDE.md)

- No new dependency, no new backend concept — this is wiring an already-
  computed, already-used classification onto one more endpoint/screen,
  nothing about the classification logic itself changes.
- Don't touch `evidence_class.py`'s classification rules, thresholds, or
  `EXPORTABLE_CLASSES` — out of scope for this task.
- Preserve the existing API contract's current fields exactly; only add
  new ones (`evidence_class`, `evidence_class_reason`) to the
  `search-by-attributes` response.
- Minimal diff: exporting and reusing `TierBadge` is preferred over a
  parallel component — if reuse turns out to be awkward for a real
  reason (e.g. tight coupling to `VehicleTimeline.jsx`'s other state),
  explain why in your summary rather than silently duplicating it.
- Test: run the existing backend suite
  (`sentinel-solution/backend`, `.venv/Scripts/python.exe -m pytest tests -v`)
  and add/extend a test for `search_by_attributes` asserting
  `evidence_class` is present and correctly reflects a plate-read vs.
  appearance-only row (mirror how existing tests for `/vehicle/recent`
  or `/vehicle/{plate}/history` verify this, if such a test exists —
  check first before writing a new pattern). Run `npm run lint` and
  `npm run build` in `sentinel-solution/frontend` — both must be clean.
  Then actually start both servers and run a real attribute search
  against the live backend with real data (e.g. from
  `scripts/demo_end_to_end.py`'s seeded scenario) and confirm the tier
  badges and banner actually render correctly for at least one CONFIRMED
  and one LEAD_ONLY row — report what you actually saw, not just that
  the build passed.
- Do not commit/push. At the end, report: what changed, files touched,
  whether `TierBadge` was successfully exported/reused or duplicated
  (and why if duplicated), test/build results, and the real end-to-end
  check you ran.
