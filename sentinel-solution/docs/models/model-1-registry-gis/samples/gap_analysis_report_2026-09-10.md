# Sample Gap-Analysis Report — Sentinel Camera Registry

Generated 2026-09-10 via a real `GET /cameras/gap-analysis` call against
the live backend (30-camera sandbox catalogue), as an
`investigator`-role principal. Raw JSON: `gap_analysis_report_2026-09-10.json`.
This is the Model 1 deliverable *"sample gap-analysis report"* — previously
only demoable live in the UI (`GapAnalysisPanel.jsx`), with no exported
sample file checked into the repo until now.

## Summary

| Metric | Value |
|---|---|
| Cameras in live sandbox catalogue | 30 |
| Cameras registered (onboarded) | 30 |
| Live but not yet onboarded | 0 |
| Onboarded but not currently live | 0 |
| Missing department assignment | 23 / 30 |
| Missing GIS coordinates | 8 / 30 |
| Currently unhealthy (no recent frame) | 21 / 30 |

## Department coverage

| Department | Cameras |
|---|---|
| Police | 1 |
| Municipal Corporation | 1 |
| GSRTC | 2 |
| Health | 1 |
| Panchayat | 2 |
| **Unassigned** | **23** |

## What this genuinely shows

- **Onboarding coverage is complete**: every camera the sandbox catalogue
  currently exposes is registered, and vice versa (0 in both drift
  buckets) — the registry's health-sync loop (`main.py`) is doing its job.
- **Department metadata is the real, honest gap**: `scripts/onboard_from_catalogue.py`'s
  keyword-based department inference only matched 7 of 30 cameras against
  their location strings (e.g. "Police", "GSRTC" appearing literally in
  the name) — the other 23 have no department assigned. This is not a
  bug, it's a heuristic reaching its limit; closing it needs either better
  keyword rules or manual department assignment per camera.
- **"Unhealthy" here reflects a point-in-time RTSP connection state**, not
  a hardware fault — a camera counted unhealthy simply hadn't produced a
  fresh frame recently when this snapshot was taken (sandbox feeds are
  scene-looping test footage, not 24/7 production streams).
- **Ageing-infrastructure detection is out of scope for this report** —
  `CameraRegistry` has no install-date/equipment-age field, so "ageing
  infra" (part of the official Model 1 spec) isn't computable from this
  endpoint yet; see the module's `IMPLEMENTATION_PLAN.md`.

## How to regenerate this report

```bash
curl -H "X-Sentinel-API-Key: <investigator-or-admin-key>" \
  http://localhost:8000/cameras/gap-analysis
```
