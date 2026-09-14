# Government-Feed Demo Video — Recording Script

Satisfies **Submission Requirement #4 / Q31 / Q33** — "government-feed
demonstration with output report" (screen-recorded video **plus** an
output report showing detected vehicles/plates with timestamps). Mock-ups
are explicitly disallowed (Q32) — everything below must be the real
backend against the real sandbox, not a re-run of the own-feed
composited scenario.

**Target length: 2–3 min**, per Q31. This is a *separate* recording from
`DEMO_SCRIPT_OWN_FEED.md` — do not reuse that footage here.

---

## Honesty guardrails (read before recording)

- **This is the government feed** — per `HACKATHON_DETAILS.md` §12, the
  hackathon's own sandbox ("~12 hours of CCTV footage from 30+ cameras
  across 5 departments... real footage, no synthetic data... served as
  simulated live video") IS the Phase 1 government-provided feed. Don't
  frame this as "waiting on organizer access" — that framing was
  retracted 2026-09-12 (`TASKS.md`) after being independently verified as
  stale. Say plainly on camera: "this is the organizer-provided sandbox
  feed," not "our own footage."
- **Lead with the real, reproducible result**: `cam06`, plate
  `GJ01RP6128`, read correctly 4/5 times, accepted at confidence 0.81
  through the actual consensus-vote logic (`tracker.py`) — not a
  cherry-picked single frame. This is documented in `HLD.md` §3 and
  locked in as a regression test
  (`test_consensus_plate_real_cam06_vehicle_clears_confidence_gate`).
- **Do NOT claim**: a specific aggregate ANPR accuracy percentage unless
  you re-state the exact measurement basis from `HLD.md` §3 (dataset,
  camera count, method) in the same breath — a bare "X% accurate" claim
  without that context is a forbidden claim per this repo's `CLAUDE.md`
  §8. Do not claim face recognition or any biometric capability — not
  built, not in scope.
- **The output report is mandatory, not optional** — Q33 requires it
  explicitly. Generate and show it on screen (Shot 5 below); don't just
  narrate that reports exist.

---

## Pre-flight (do this before you hit record)

From `sentinel-solution/backend`, real `.venv` with `requirements-ml.txt`
installed (paddleocr confirmed installed on this machine as of
2026-09-13 — verify again on whichever machine actually records):

```bash
# 1. Start the backend against the REAL sandbox (needs real sandbox
#    credentials set — SENTINEL_ACCESS_EMAIL / SENTINEL_ACCESS_TOKEN).
python -m app.main                     # http://localhost:8000
#    -> note the bootstrap admin API key printed on first run.

# 2. Start the frontend (separate terminal).
cd ../frontend && npm run dev          # http://localhost:5173
```

In the browser, paste the admin API key into the API-key bar. Confirm
live sandbox connectivity first (don't discover a dead session on
camera): open the Live Map / camera grid and check `cam06` shows
`is_healthy` and plays.

**Recording setup:** 1920×1080, hide bookmarks/personal tabs, browser
zoom 110–125%, cursor highlighting on. Calm voiceover or on-screen
captions following the script below.

---

## Shot-by-shot

### SHOT 1 — Frame the feed honestly (0:00–0:20) · *browser, camera list/registry*

**On screen:** the camera registry showing all 30 onboarded sandbox
cameras, department tags visible (Police, Municipal Corporation, GSRTC,
Health, Panchayat).

**Narration:**
> "This is Sentinel connected to the hackathon's own government-provided
> CCTV sandbox — real footage from 30-plus cameras across five Gujarat
> departments, not our own recorded footage. Everything from here is the
> live backend against this real feed."

### SHOT 2 — Live connection proof (0:20–0:45) · *Live Map / camera tile for cam06*

**On screen:** `cam06`'s live HLS tile actually playing (real motion),
health status visible as connected/healthy.

**Narration:**
> "Here's camera 6, streaming live from the sandbox over RTSP, proxied
> through our authenticated HLS pipeline. This is real video, playing
> right now — not a recording of a recording."

### SHOT 3 — Real ANPR on this feed (0:45–1:25) · *ANPR/vehicle detail for cam06, or terminal tailing detection logs*

**On screen:** either (a) the camera detail / last-detection panel for
`cam06` showing a real accepted plate read, or (b) a terminal tailing
`sentinel.db` inserts / backend logs as a real detection lands, timestamp
visible.

**Narration:**
> "This vehicle's plate, GJ01RP6128, was read correctly on four of five
> passes and accepted by our temporal consensus-vote logic at 0.81
> confidence — the real YOLOv8-plus-PaddleOCR pipeline running against
> this exact camera, not a staged frame."

### SHOT 4 — Searchable movement + watchlist correlation (1:25–2:00) · *Vehicle Tracking tab*

**On screen:** search `GJ01RP6128` (or another plate with real sandbox
sightings if a cross-camera reappearance exists at record time — check
this beforehand and pick whichever plate has the strongest real timeline).
Purpose + case ID filled in. Timeline renders with real timestamps and
camera IDs.

**Narration:**
> "Given only the registration number, Sentinel returns the real,
> timestamped, camera-by-camera movement history from this live feed —
> and automatically checks it against the watchlist."

*(If this plate isn't watchlisted, say so plainly — "not currently
watchlisted" — rather than implying an alert that didn't fire.)*

### SHOT 5 — The mandatory output report (2:00–2:30) · *Reports tab*

**On screen:** open the Reports view, generate the **"Vehicle detections
report"** (reuses `GET /vehicle/recent` — camera, plate, timestamp,
evidence class per row), show the downloaded file open with real rows
visible — timestamps and camera IDs legible on screen.

**Narration:**
> "Per the submission requirement, here is the actual output report —
> every detected vehicle, its plate, the camera, and the timestamp,
> exported directly from the running system, not compiled by hand."

### SHOT 6 — Close (2:30–2:45, optional)

**On screen:** brief cut back to the camera registry or map.

**Narration:**
> "This is the same backend, the same registry, the same evidence rules
> shown in our own-feed demo — running end to end against the
> organizers' real sandbox feed."

---

## Coverage check — every mandatory beat is on screen

| Q31/Q33 requirement | Shot |
|---|---|
| Government-feed demonstration (real feed, not own footage) | 1, 2 |
| AI detection & analytics (ANPR) on that feed | 3 |
| Searchable movement / watchlist correlation | 4 |
| **Output report — detected vehicles/plates with timestamps** | 5 |
| Fully functional backend (no mockup) | Implicit throughout — live tiles, live search, live report generation |

---

## Known gaps to disclose if asked, not to hide

- GIS coordinates: 22 of 30 sandbox cameras have coordinates (from our
  registry, not the sandbox catalogue, which supplies none) — 8 don't.
  Don't claim full statewide GIS coverage from this sandbox alone.
- The fresh live-detection moment (Shot 3) depends on the ML runtime
  actually producing a new event during the recording window — rehearse
  this beat once beforehand so you know it fires, rather than hoping live
  on the actual take. If it doesn't fire in time, fall back to showing
  the historic real scan result (`data/anpr_scan/20260905T112430Z`) and
  say plainly it's a prior real run, not this session's.
- Don't claim a specific statewide accuracy number — this sandbox is 30
  cameras, not 80,000; keep scalability claims in the HLD/scalability
  doc, not this video.
