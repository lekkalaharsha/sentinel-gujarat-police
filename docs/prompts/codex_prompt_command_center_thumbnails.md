# Task for Codex — show real evidence-crop thumbnails in Command Center's "Recent detections"

Read `CLAUDE.md` at the repo root (and `sentinel-solution`'s if present)
first and follow it — especially the honesty rules (§24.5, §24.11) and
minimal-diff rule (§24.1). Do not commit/push — leave changes in the
working tree.

## Why

`CommandCenter.jsx`'s "Recent detections" panel (the live-polled list on
the Command Center screen) currently renders a generic vehicle silhouette
icon (`<IconVehicleSide />`, inside a `.vehicle-thumb2` box) for every
row, even though the backend already tells the frontend whether a real
evidence photo exists for that sighting (`GET /vehicle/recent`'s
`has_evidence_image` field, already present in the row data —
`CommandCenter.jsx` line ~83 already has access to `r.has_evidence_image`
via `r`, it's just not used). The user wants the actual detection photo
shown here, not a placeholder icon, whenever one was really captured.

## What already exists — reuse it, don't rebuild it

- **Backend**: `GET /vehicle/event/{event_id}/crop` already serves the
  real saved crop image (`routes_vehicle.py`) — RBAC-gated
  (`require_role("viewer")`, department-scoped, audit-logged on
  cross-department access), returns 404 if the event has no crop. This
  endpoint is complete; do not modify it.
- **Frontend fetch pattern**: `api.js` already has `eventCropBlobUrl` —
  fetches the crop as an authenticated blob (a plain `<img src>` can't
  carry the API-key header) and returns an object URL. Reuse this
  exactly, don't write a second fetch path.
- **Frontend display pattern**: `EvidenceViewer.jsx` already wraps that
  fetch into a component with an honest placeholder ("No evidence image
  saved for this sighting" / loading / error states) — but it's styled
  for a larger detail view (`.evimg2`, with a label overlay), not a
  compact 48×36px row thumbnail. Don't force-fit the full component here
  if its styling doesn't suit a thumbnail — either reuse its internal
  blob-loading logic in a smaller thumbnail-specific render, or (simpler
  and preferred) build a small inline thumbnail using the same
  `api.eventCropBlobUrl` call directly, matching this file's own
  reasoning — your call on which is cleaner, but do not duplicate the
  auth-blob-fetching logic itself; `eventCropBlobUrl` is the one place
  that exists.

## What to change

In `CommandCenter.jsx`'s "Recent detections" row rendering
(`.detectrow2`, around line ~81-89):

- Replace the current unconditional `<IconVehicleSide />` inside
  `.vehicle-thumb2` with: the real crop thumbnail when
  `r.has_evidence_image` is true (fetched via `eventCropBlobUrl(r.event_id)`
  or however you wire the reuse above), falling back to the existing
  `<IconVehicleSide />` icon when `r.has_evidence_image` is false — never
  show a broken image or a permanently-loading spinner as the fallback.
- Keep the existing `.vehicle-thumb2`/`.watch2` sizing and watchlist-red
  styling intact — the box is small (48×36px) and sits in a list of up to
  12 rows polled every 8s, so this must stay a lightweight thumbnail, not
  a large image. `object-fit: cover` (or similar) so real photos don't
  distort inside the fixed box — check `.evimg2 img`'s existing
  `object-fit: contain` rule for the pattern this repo already uses
  elsewhere, but pick whichever fits a small fixed-aspect thumbnail
  correctly (likely `cover`, not `contain`, given the box is fixed-size
  unlike `.evimg2`'s flexible one — use judgement, don't just copy the
  larger view's rule if it doesn't fit).
- **Loading/failure behavior**: this list re-polls every 8 seconds and
  can hold up to 12 rows — don't re-fetch the same event's blob on every
  poll tick if the row for that `event_id` didn't change (avoid a memory/
  network leak of ever-growing object URLs). Revoke object URLs you
  created when a row's thumbnail is replaced or unmounted (`URL.revokeObjectURL`
  — check how `api.js`'s existing blob-URL callers already handle this,
  if any, and follow that convention).
- Don't change the crop's authorization/visibility rules — a LEAD_ONLY
  sighting's crop is viewable here exactly as `routes_vehicle.py`'s own
  docstring intends (view is not gated on evidence class, only export
  is) — this task is UI-only, no policy change.

## Constraints (from this repo's CLAUDE.md)

- No new backend endpoint, no new dependency — this is purely wiring an
  existing endpoint into an existing panel via the existing blob-fetch
  helper.
- No fabricated placeholder photo — an event with `has_evidence_image:
  false` (or a 404 from the crop endpoint despite the flag being true —
  handle that edge case too, since the flag and the on-disk file can in
  theory disagree per the endpoint's own docstring) must show the plain
  icon/placeholder, never a stock or generic vehicle photo.
- Minimal diff: touch `CommandCenter.jsx` (and `EvidenceViewer.jsx` only
  if you factor out shared logic from it — don't duplicate its fetch
  logic if extracting is easy; don't force a refactor of it if reuse
  turns out awkward, just explain why in your summary).
- Test: run `npm run lint` and `npm run build` in
  `sentinel-solution/frontend` — both must be clean. Then actually start
  the backend (`sentinel-solution/backend`, `.venv/Scripts/python.exe -m
  app.main`) and frontend (`npm run dev`), open Command Center with a
  real admin/viewer key, and confirm real thumbnails render for rows that
  have `has_evidence_image: true` and the icon fallback renders for rows
  that don't — report what you actually saw on screen, not just that the
  build passed. If the local DB has zero rows with a saved crop to test
  against, say so plainly rather than claiming an unverified visual
  result.
- Do not commit/push. At the end, report: what changed, files touched,
  whether you reused `EvidenceViewer`'s logic or wrote a smaller inline
  version (and why), how you handled object-URL cleanup across re-polls,
  lint/build results, and the real on-screen check you performed.
