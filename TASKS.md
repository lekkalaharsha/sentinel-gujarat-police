# Sentinel — Next Actions

Living task list. Deadline **7 September 2026** (Phase 1), event 10–11 Sep.
Last updated **2026-09-04**. Cross-check against `REQUIREMENTS_COVERAGE.md`
(the authoritative deliverable-status matrix) and `sentinel-solution/README.md`
("Known issues") before trusting this file if it's more than a day or two old
— both decay fast and this file summarizes them, not the other way round.

## P0 — hard submission blockers

- [ ] **Run `scripts/onboard_from_catalogue.py` before recording ANY video.**
      Confirmed 2026-09-04 by actually loading the UI: the backend has all
      30 real sandbox cameras live-streaming (`/health` shows 30 active
      workers), but the Map & Registry tab — the first thing anyone sees —
      shows **"Camera registry (0) — No cameras onboarded yet."** The live
      RTSP worker state and the Model 1 `CameraRegistry` DB table are
      separate; nothing populates the registry automatically. Recording a
      demo video against this right now would open on an apparently-broken,
      empty app. Review the script's department-keyword inference output
      before trusting it (README already flags this), but run it first.
- [ ] **Record the own-feed demo video** (§9.3, 2–3 min, must show a real
      working backend, no mock-ups). Doesn't need the sandbox — unblocked
      now. Script: `DEMO_SCRIPT_OWN_FEED.md` +
      `scripts/demo_end_to_end.py` with `SENTINEL_DEMO_PERSIST=1`, then
      `python -m app.main` + `npm run dev` and screen-record the UI walkthrough.
      **This is the single highest-leverage remaining task — nothing else
      blocks submission harder than having zero video progress.**
- [ ] **Record the government-feed demo video** (§9.4, live/recorded feed +
      screen-recorded output report of detected plates/timestamps). Sandbox
      access is now confirmed working (2026-09-04 fix) — this is genuinely
      unblocked, not still gated. Run against real `cam01`–`cam30`.
- [x] Solution Presentation (PPT) — v2 done 2026-09-04
      (`Sentinel_Solution_Presentation.pptx`, 20 slides): real flowchart
      diagrams with connector arrows, Bahnschrift/Segoe UI typography, far
      less text per slide, references slide added. v1 kept as
      `Sentinel_Solution_Presentation_v1.pptx`. Regenerate via
      `deck-build/build_deck_v2.py` — visually re-verify via PowerPoint COM
      export (see script comments); python-pptx opening the file
      successfully is NOT sufficient proof it's valid, see the float-EMU
      bug noted in project memory.
- [x] Technical Proposal / HLD — `sentinel-solution/HLD.md`
- [x] Scalability Strategy — `sentinel-solution/SCALABILITY.md`

## P1 — do before the videos if time allows (raises what the videos show)

- [ ] Measure real-footage OCR accuracy against actual sandbox camera
      footage (currently only verified against clean synthetic plate text —
      this is the single most jury-visible unmeasured number per HLD.md §5
      and the risk register).

## P2 — known code issues from the 2026-09-04 review, not yet fixed

Ranked by how likely each is to visibly misbehave during a live demo:

- [ ] **RTSP discontinuity detection doesn't survive a reconnect** —
      `last_pts_ms` resets to `None` on every reconnect, so a scene-loop
      point that triggers a full reconnect (vs. a smooth PTS-backward moment
      inside one connection) goes undetected and tracker/identity state
      isn't reset. (`streaming/rtsp_client.py`)
- [ ] **No FFmpeg read-timeout on `cap.read()`** — a stalled TCP session can
      block forever instead of returning `ok=False`, which would silently
      defeat the otherwise-correct backoff/reconnect logic.
      (`streaming/rtsp_client.py`)
- [ ] **Frontend: Safari's native-HLS path sends no API key** and fails with
      no visible error banner (only the hls.js path attaches auth headers).
      (`frontend/src/components/LiveView.jsx`)
- [ ] **Frontend: map view doesn't distinguish OBSERVED vs. INFERRED route
      segments** — draws one uniform line regardless of link confidence,
      unlike the Vehicle Tracking timeline panel which does this correctly.
      (`frontend/src/components/MapView.jsx`, `App.jsx`)
- [ ] **Frontend: alert-list polling can race a user's transition click** —
      briefly reverts a just-acknowledged alert, second click then hits a
      confusing raw `409 illegal transition` error.
      (`frontend/src/components/AlertsPanel.jsx`)
- [ ] **Frontend: stale plate-search race** — no request sequencing means a
      slow first search can overwrite a faster second one, showing one
      plate's number with another plate's history. (`VehicleSearch.jsx`)
- [ ] **Possible SSRF/credential-leak gap in the HLS proxy** if
      `authenticated_get` follows redirects to a third-party host — not
      fully ruled out. (`routes_stream.py`, `catalogue.py`)
- [ ] Two endpoints return `{"error": ...}` with HTTP 200 instead of a
      proper 400/404 (`routes_auth.py` create-key, `routes_cameras.py`
      get-camera) — cheap sweep-fix.
- [ ] `VehicleIdentity` history lookup uses `.first()` on a non-unique-by-
      construction query pattern — verify `identity.py` can't produce two
      rows for one plate through any path other than the race already
      fixed; if it can, `routes_vehicle.py`'s history endpoint silently
      drops sightings with no indication anything was omitted.
- [ ] `search_by_attributes` truncates to 200 results with no total-count
      signal — an investigator can get zero recent hits with no indication
      results were cut off. (`routes_vehicle.py`)

## P3 — nice-to-have if time remains

- [ ] Multi-camera grid / video wall (Model 2 feature, not built)
- [ ] Sample gap-analysis PDF export (endpoint exists, no exported sample)
- [ ] Department-scoped RBAC (schema supports it, filter not implemented)
- [ ] WHEP low-latency preview (HLS-via-proxy is the working path; low
      priority — not required by the test case)

## Deliberately not doing (see STRATEGY.md's OUT list — don't silently build these)

Face recognition, fingerprint/biometric integration, full 80k-camera
physical ingestion, a new VMS, real per-vendor VMS federation middleware,
actually deploying Kafka/MediaMTX this week.

## How to verify any fix in this list

Per this project's CLAUDE.md: don't declare a fix done from a syntax check.
Exercise it with `scripts/demo_end_to_end.py` (real models) and/or a live
request against `python -m app.main`, including the failure mode it's
supposed to handle — not just the happy path.
