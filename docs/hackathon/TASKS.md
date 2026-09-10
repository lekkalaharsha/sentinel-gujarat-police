# Sentinel — Next Actions

Living task list. Deadline **15 September 2026** (Phase 1, updated
2026-09-05 — was 7 Sep), event 22–23 Sep (was 10–11 Sep).
Last updated **2026-09-05** (reconciled against actual code — several
entries below were stale/already fixed and have been corrected).
Cross-check against `REQUIREMENTS_COVERAGE.md` (the authoritative
deliverable-status matrix) and `sentinel-solution/README.md` ("Known
issues") before trusting this file if it's more than a day or two old.

## P0 — hard submission blockers

- [ ] **Re-verify camera-registry auto-population before recording video.**
      Originally: "backend has 30 live workers but registry shows 0
      onboarded." **Partially stale** — `main.py`'s health-sync loop
      auto-creates a bare `CameraRegistry` row for any active worker
      (confirmed empirically 2026-09-05: a fresh DB showed "Onboarded 30"
      with zero manual onboarding calls). What's still missing is
      department/GIS metadata on those auto-created rows — run
      `scripts/onboard_from_catalogue.py` for that, but the "empty-looking
      app" risk from the original note is likely gone. Confirm this on the
      actual recording machine before trusting it, not just this note.
- [ ] **Record the own-feed demo video** (§9.3, 2–3 min, must show a real
      working backend, no mock-ups). Script: `DEMO_SCRIPT_OWN_FEED.md` +
      `scripts/demo_end_to_end.py` with `SENTINEL_DEMO_PERSIST=1`, then
      `python -m app.main` + `npm run dev` and screen-record the UI walkthrough.
      **Organizer guidance received 2026-09-05** (their core team, relayed
      by the user): for this demo, using any clearly-visible real sandbox
      camera is fine — no longer needs to be literally "our own feed."
      `cam06` (a real, close-range, front-facing camera identified today)
      now has a genuinely strong headline result: a real car's plate
      (`GJ01RP6128`) read correctly 4/5 times, confirmed via the actual
      `tracker.py` consensus-vote logic to produce an accepted
      confidence-0.81 read — not just a promising OCR string (see `HLD.md`
      §3). **Lead the video with this real result**, not the
      synthetic-composite montage. Still need the terminal "it's real"
      proof shot, captions, and final `ffmpeg` concatenation. **Still the
      single highest-leverage remaining task.**
- [x] ~~Record the government-feed demo video~~ (§9.4) — **externally
      blocked, per organizer guidance 2026-09-05**: the hackathon's own
      core team said their sandbox is still being fixed on their end for
      this specific test case. Don't force this recording; revisit once
      they signal it's ready. (The HLS live-view proxy bug that was
      independently blocking this — a CDN User-Agent gate — is fixed on
      our side regardless, so we're ready the moment their sandbox is.)
- [x] Solution Presentation (PPT) — v2 done 2026-09-04.
- [x] Technical Proposal / HLD — `sentinel-solution/docs/HLD.md`
- [x] Scalability Strategy — `sentinel-solution/docs/SCALABILITY.md`
- [x] Real-footage ANPR accuracy measurement — done 2026-09-05, corrected
      twice same day, now conclusively positive: initial scan found 0
      reads with only wide-overview cameras inspected; reviewing all 30
      cameras found `cam06` (close-range, ANPR-suitable) and a second real
      bug (two-line-plate/homoglyph matching in `anpr.py`) — fixed. A full
      30-camera re-scan with both fixes then found a real car's plate
      (`GJ01RP6128`) read correctly 4/5 times, confirmed via the actual
      production consensus-vote logic to produce an ACCEPTED
      confidence-0.81 read. Real, correct, end-to-end ANPR on live
      government sandbox footage — not a promising string, the real
      accept-path, locked in as a regression test
      (`test_consensus_plate_real_cam06_vehicle_clears_confidence_gate`).
      See `HLD.md` §3.
- [x] HLS proxy 502/403 — done 2026-09-05 (CDN User-Agent gate, fixed in
      `catalogue.py`).
- [x] ANPR two-line-plate + homoglyph OCR bug — done 2026-09-05, see above.

## P1 — do before/alongside the videos if time allows

- [x] **Stale-search race — fixed 2026-09-10.** Confirmed the race
      survived the frontend rebuild in both `VehicleIntelligence.jsx` and
      `SearchView.jsx` (`submit()` in each fired a plain `fetch` with no
      request-sequencing, so a slow first search could overwrite a faster
      second search's results). Fixed with an `AbortController` per
      submit in both components: the previous in-flight request is
      aborted before a new one starts, and `api.js`'s `vehicleHistory`/
      `searchByAttributes` now accept and forward a `signal`. Verified
      with `npm run build` (clean) and `npm run lint` (no new warnings);
      not click-tested in a live browser this session (no browser
      automation tool available) — worth a manual double-search check
      before the demo.
- [x] **`create_api_key` 200-vs-400 — fixed 2026-09-10.** `routes_auth.py`
      now imports `HTTPException` and raises `HTTPException(400, "role
      must be one of admin, investigator, viewer")` for an invalid role
      instead of returning `{"error": ...}` with HTTP 200. Regression
      coverage added in `tests/test_auth.py`
      (`test_invalid_role_raises_400`, `test_valid_role_creates_key`);
      full suite re-run, 45/45 passed.
- [x] **`search_by_attributes` truncation — fixed 2026-09-10.**
      `routes_vehicle.py` now runs a `count()` query alongside the
      limited fetch and returns `total_count`/`truncated: total_count >
      200` in the response; switched ordering from oldest-first
      (`asc()`) to newest-first (`desc()`) so a truncated response
      surfaces the most recent matches rather than silently dropping
      them. `SearchView.jsx` now shows "N of M total" and a truncation
      notice when applicable. Regression coverage added in
      `tests/test_vehicle_search.py`; full suite re-run, 47/47 passed.
      `npm run build`/`npm run lint` both clean, no new warnings.
- [x] **Gap-analysis PDF export — fixed 2026-09-10.** Added
      `GET /cameras/gap-analysis/export.pdf` (`routes_cameras.py`),
      reusing the same `_compute_gap_analysis` data as the existing JSON
      endpoint (no second, independently-computed report) and rendering
      via `reportlab` (added to `requirements.txt`, not previously a
      dependency) — summary table, cameras-by-department breakdown, and
      each gap category's camera-id list. Same department-scoping as the
      JSON endpoint and the CSV export. `GapAnalysisPanel.jsx` got an
      "Export PDF" button (`api.js`'s `downloadGapAnalysisPdf` — fetches
      as a blob since the API key is a custom header, not a cookie, so a
      plain `<a href>` can't authenticate). Regression coverage in
      `tests/test_gap_analysis_pdf.py` (including a real bug caught by
      the empty-department-breakdown test: `[header] + [rows] or
      [fallback]`'s `or` never fires because concatenation is always
      truthy — fixed with explicit parens before it shipped). A real
      sample PDF was generated end-to-end against the live 30-camera
      sandbox catalogue (not synthetic data) via a temporary,
      immediately-revoked admin key and saved to
      `docs/assets/sample_gap_analysis_report.pdf` for the submission.
      Full backend suite re-run, 50/50 passed; `npm run
      build`/`npm run lint` both clean.
- [x] **Doc-honesty points — closed 2026-09-10.**
      1. **Multi-vendor wording** — `docs/submission/EMAIL_DRAFT.md`
         reworded: no longer implies proven integration with
         VISWAS/NETRAM/TRINETRA, now explicit that this submission
         demonstrates the architecture against the hackathon sandbox,
         not a live connection to those systems.
      2. **Private/commercial CCTV coverage** — added a paragraph to
         `HLD.md`'s onboarding section: same onboarding flow as
         departmental cameras, tagged by owning entity, contingent on
         that entity's access grant; explicitly labeled design-only, not
         built or demonstrated.
      3. **External-DB integration honesty** — confirmed already closed,
         `HLD.md`'s "query, don't copy" principle already states this
         explicitly for VAHAN/SARTHI/eGujCop/CCTNS.
      `MODULE_GAP_ANALYSIS.md`'s discussion points section updated to
      mark all 3 resolved. Docs-only change, no code touched.
- [ ] `CODEX_HANDOFF_PROMPT.md`'s ML-3: empirically justify
      `EMBEDDING_SIMILARITY_THRESHOLD=0.80` — still blocked on lacking
      same-vehicle real-footage pairs; the extended deadline may make this
      newly worth attempting (e.g. a controlled test driving one vehicle
      past 2+ real sandbox cameras) rather than deferring further.
- [ ] **New 2026-09-05:** per-character (or position-weighted) consensus
      voting in `tracker.py`'s `consensus_plate()` — currently exact-string
      majority vote, which splits `cam06`'s real 8-valid-reads-out-of-13
      across ~6 distinct near-matching strings (below the 0.5 confidence
      floor). A character-level vote per position would likely recover a
      single confident read from the same real data. See `HLD.md` §3 for
      the full context.

## P2 — known code issues, not yet fixed (lower demo-visibility risk)

- [ ] **RTSP discontinuity detection doesn't survive a reconnect** —
      `last_pts_ms` resets to `None` on every reconnect, so a scene-loop
      point that triggers a full reconnect (vs. a smooth PTS-backward
      moment inside one connection) goes undetected and tracker/identity
      state isn't reset. (`streaming/rtsp_client.py`)
- [ ] **No FFmpeg read-timeout on `cap.read()`** — a stalled TCP session
      can block forever instead of returning `ok=False`, defeating the
      otherwise-correct backoff/reconnect logic. (`streaming/rtsp_client.py`)
- [ ] **Frontend: Safari's native-HLS path sends no API key** and fails
      with no visible error banner (only the hls.js path attaches auth
      headers). (`frontend/src/components/LiveView.jsx`)
- [ ] **Frontend: map view doesn't distinguish OBSERVED vs. INFERRED route
      segments** — draws one uniform line regardless of link confidence,
      unlike the Vehicle Tracking timeline panel which does this correctly.
      (`frontend/src/components/MapView.jsx`, `App.jsx`)
- [ ] **Frontend: alert-list polling can race a user's transition click** —
      briefly reverts a just-acknowledged alert, second click then hits a
      confusing raw `409 illegal transition` error.
      (`frontend/src/components/AlertsPanel.jsx`)

~~VehicleIdentity history lookup uses `.first()` on a non-unique query
pattern~~ — **not actually a bug**, re-verified 2026-09-05: `vehicle_identity
.plate` has had a partial-unique DB constraint since 2026-09-04, so
`.filter(plate==...).first()` can structurally never match more than one
row. Remove from backlog.

~~Possible SSRF/credential-leak gap in the HLS proxy~~ — **already fixed**,
per `REVIEW_FINDINGS.md`'s `SEC-doc` entry (host-allowlist check +
`allow_redirects=False`) — this TASKS.md entry was stale, not a real open
item.

## P3 — nice-to-have if time remains

~~Multi-camera grid / video wall~~ — **done 2026-09-05** (`CameraGridView.jsx`).
~~Department-scoped RBAC~~ — **done 2026-09-05** (`api/auth.py`'s `department_scope`).
- [ ] WHEP low-latency preview (HLS-via-proxy is the working path; low
      priority — not required by the test case).
- [ ] Backend search/filter query params on `/cameras` (currently
      client-side only in the frontend).
- [ ] Coverage-radius/zone GIS map layer, ageing-infrastructure tracking
      (install-date field).
- [ ] Camera-onboarding audit trail (who onboarded/edited which camera —
      `AuditLog` currently only covers vehicle-search purpose/case_id).

## Deliberately not doing (see STRATEGY.md's OUT list — don't silently build these)

Face recognition, fingerprint/biometric integration, full 80k-camera
physical ingestion, a new VMS, real per-vendor VMS federation middleware,
actually deploying Kafka/MediaMTX this week.

## How to verify any fix in this list

Per this project's CLAUDE.md: don't declare a fix done from a syntax check.
Exercise it with `scripts/demo_end_to_end.py` (real models) and/or a live
request against `python -m app.main`, including the failure mode it's
supposed to handle — not just the happy path.
