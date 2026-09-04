# Requirements Coverage — Official Problem Statement → Our Status

Mapped 2026-09-03 against the **official** Sentinel problem statement (pasted
in full by the user; consistent with `HACKATHON_DETAILS.md`, incl. the
₹51,00,000 prize pool). Status labels are honest and code-verified where
claimed:

- ✅ **Done** — built and exercised end-to-end against real code
- 🟡 **Partial** — core built, a piece is stubbed/unproven
- ⛔ **Not started** — required, no work yet
- 🔵 **Deliberate scope-out** — intentionally not built, reason stated
- 📄 **Doc/asset task** — no engineering, just needs producing/exporting

Deadline: **2026-09-07** (Phase 1). We are a **Model 1 + Model 2 hybrid**;
Models 3/4 are documented roadmap, not built (STRATEGY.md).

---

## A. Model 1 — Central CCTV Registry & GIS (mandatory foundation)

| Official deliverable | Status | Where |
|---|---|---|
| Registry portal with GIS map view | ✅ Done | React + Leaflet, health-colour-coded (`frontend/`, Model 1 tab) |
| Bulk + manual + API onboarding | ✅ Done | `POST /cameras`, `/cameras/bulk`, Registry Ops form |
| Camera health / maintenance-status monitoring | ✅ Done | `is_healthy`/`last_seen_live_at` from real RTSP worker state |
| Gap-analysis report for uncovered/ageing zones | ✅ Done (endpoint) / 📄 (sample report) | `GET /cameras/gap-analysis` — export a sample PDF for submission |
| Role-based search/filter/export + metadata audit trail | 🟡 Partial | RBAC + audit log ✅; export/filter UI is thin |
| Sample onboarded camera-metadata dataset | 🟡 Partial | `scripts/onboard_from_catalogue.py` exists, **not run vs live sandbox** |
| Registry API documentation | ✅ Done (auto) | FastAPI OpenAPI at `/docs` — reference it in the submission |

## B. Model 2 — Unified Viewing & Metadata Analytics (mandatory pair)

| Official deliverable | Status | Where |
|---|---|---|
| Unified viewer connected to ≥2 different systems | 🟡 Partial | HLS-via-authenticated-proxy live view works; "≥2 different systems" needs the real ~50-cam sandbox |
| ANPR-based metadata generation | ✅ Done (real, verified on synthetic) / 🟡 (real footage unproven) | YOLOv8 → plate crop → PaddleOCR → regex validate → temporal fusion |
| Event tagging + camera-wise indexing | ✅ Done | `VehicleEvent` per sighting, indexed by camera/plate/time |
| Searchable vehicle-movement records | ✅ Done | `GET /vehicle/{plate}/history`, `/vehicle/search-by-attributes` |
| Multi-camera grid / video walls | ⛔ Not started | Single live-view today; grid not built |
| Alerts for tagged events / vehicles of interest | ✅ Done | Watchlist engine + governed alert lifecycle |
| Architecture note: existing dept systems unaffected | ✅ Done | HLD §3 (direct-connect, no middleware, VMS keep running) |

## C. Mandatory Test Case (§ Test Scenario)

| Requirement | Status | Notes |
|---|---|---|
| Onboard ~50 heterogeneous cameras | 🟡 Partial | Onboarding pipeline ✅; needs live sandbox access to actually do the 50 |
| Identify/trace a designated vehicle by **registration number** | ✅ Done | Core path, verified end-to-end |
| Complete **timestamped, location-wise** route/movement history | ✅ Done | `/vehicle/{plate}/history` — per-camera timeline **+ geo-temporal route reconstruction**: OBSERVED sightings interleaved with honestly-labelled INFERRED camera-less segments (`analytics/geo.py`), rendered in the timeline UI. Directly targets the "advanced cross-camera correlation" bonus. |
| Cross-reference live feeds vs **representative watchlist** | ✅ Done | Own watchlist (allowed) + real-time alert on match |
| Automated **real-time alert** on match | ✅ Done | Alert row → polled UI, governed lifecycle |
| Cross-camera continuity when plate unreadable | ✅ Done (our differentiator) | Appearance-second identity resolution, retroactive plate upgrade |

## D. Submission Documents (all mandatory)

| Deliverable | Status | Notes |
|---|---|---|
| 1. Solution Presentation (PPT/PDF) | ✅ Done (v2) | `Sentinel_Solution_Presentation.pptx` (20 slides) — v2 redesign 2026-09-04: real flowchart-shape diagrams with connector arrows (not text-box rectangles), Bahnschrift/Segoe UI type pairing, ~50% less text per slide, a references/sources slide. `Sentinel_Solution_Presentation_v1.pptx` kept as fallback. Built from and consistent with HLD.md/SCALABILITY.md; every slide visually verified via real PowerPoint COM export-to-PNG, not just python-pptx round-trip (a real bug — Python 3 true-division producing float EMU values, which corrupted the file for real PowerPoint despite python-pptx reading it back fine — was caught this way and fixed). Regenerate via `deck-build/build_deck_v2.py`. |
| 2. Technical Proposal / HLD | ✅ Done | `HLD.md` (verified against real runtime) |
| 3. Demo video — own feed (2–3 min, **must be a working backend**, no mockups) | ⛔ **Not started** | Can record now on synthetic/own footage; backend is functional |
| 4. Live demo — govt feed + output report (plates + timestamps) | ⛔ Blocked | Needs sandbox access; **live-footage OCR accuracy unproven** |
| Plan for Scale (compute/GPU/bandwidth/storage/HA-DR/cost) | ✅ Done | `SCALABILITY.md` |

## E. Common Evaluation Areas (§A) — how we'd score today

| Area | Our standing |
|---|---|
| 01 Successful test case (govt feed) | ⚠️ Gated on sandbox access + live-OCR proof |
| 02 Solution presentation | ⛔ PPT not started (HLD strong) |
| 03 Solution architecture | ✅ Strong — HLD/SCALABILITY, verified, honest gaps |
| 04 Working platform & demonstration | 🟡 Backend real & boots; demo videos not recorded |
| 05 Video analytics output | ✅ Vehicle analytics real; ⚠️ real-footage accuracy unmeasured |
| 06 Scalability & PoC readiness | ✅ Documented + edge-inference design |
| 07 Submission completeness | ⛔ Missing PPT + 2 videos |

## F. Bonus Consideration (§B) — we hit most

- ✅ Innovative hybrid architecture (Model 1+2, documented Model 3/4 path)
- ✅ Advanced cross-camera vehicle tracking / correlation (our core)
- ✅ Analytics beyond ANPR (dwell / speed / direction; attribute search)
- ✅ Edge-processing / bandwidth-optimisation story (SCALABILITY.md)
- ✅ Cybersecurity / privacy / auditability / RBAC (real, not checklist)
- ✅ Operational dashboards, automated alerts, health monitoring, APIs

---

## Deliberate scope-outs (stated, not hidden) — the honest tensions

| Item | Where the problem mentions it | Our decision |
|---|---|---|
| **Facial Recognition (FRS)** | HLD deliverable #4 (as an *example* tech "such as… proposed by the team"); Model 4 feature | 🔵 **Out** — DPDP risk + NIST-documented demographic bias; **not** in the mandatory vehicle test case (§Test Scenario). Frame as a deliberate, defensible governance choice; note the FRS *seam* could be added under Model 4 if a department mandates it. |
| **Person tracking / missing-person / unidentified-body** | Background DB list; watchlist examples | 🔵 Mostly out — we're vehicle-first. Watchlist supports person-type entries by plate/vehicle association, but no person Re-ID / soft-biometrics. |
| **Live govt-DB integration** (VAHAN/SARTHI/eGujCop/AFIS/NAFIS) | Background; Model 4 "integration readiness" | 🔵 Design-only ("query, don't copy"). Local representative watchlist is what the test case actually requires — that's built. |
| **VMS federation middleware (Model 3)** | Model 3 | 🔵 Roadmap — a half-built federation bus is worse than an honest documented path. |
| **Multi-camera grid / video wall** | Model 2 feature | ⛔ Not built — candidate quick add if time allows. |

---

## Sandbox access — RESOLVED 2026-09-04 (was blocker #1)

**Not an access problem — two code bugs.** The sandbox account/token were
always valid. `catalogue.py`'s CDN login only sent `password`, but
`/auth/login` requires **both** `email` and `password`; the missing field
made every login attempt silently fail while `_login()`'s broken
success-check (following redirects before checking status) reported it as
succeeding anyway. Separately, RTSP/WHEP were updated to require
`email:password@` embedded in the URL (percent-encoded `@`), which the
catalogue's URL builder didn't do at all. Both fixed in `catalogue.py`; see
`HACKATHON_DETAILS.md` §13a for the corrected auth flow. **Verified
end-to-end against the real sandbox 2026-09-04:** CDN login succeeds,
`cameras.json` returns all 30 real cameras, and a live RTSP connection to
real `cam01` over TCP returned actual decoded frames (1080×1920) with PTS
timestamps.

Also found and fixed the same day (see `sentinel-solution/README.md`'s
"Known issues, fixed" for detail): a ByteTrack id-handoff bug that forked
every vehicle into two disconnected tracks once the real detector was
wired in, and a cross-camera identity race that could create duplicate
`VehicleIdentity` rows for one plate under concurrent camera threads (now
DB-constrained + handled).

## The remaining priority order (what actually moves the score, ~3 days left)

1. **Record the own-feed demo video** (D3) — backend is functional now; doesn't need the sandbox. The last hard-blocking submission gap.
2. **Run the live govt-feed test case now that access works** (D4, E01, E05) — onboard real cameras via `onboard_from_catalogue.py`, measure real-footage OCR accuracy, record the screen-capture + output report.
3. Nice-to-have if time: multi-camera grid (Model 2), sample gap-analysis PDF export, the remaining lower-severity findings from the 2026-09-04 code review (see README "Known issues, not yet fixed").

~~Build the Solution Presentation (D1)~~ — **done, 2026-09-04.**

**Bottom line:** the *engineering* for the mandatory Model 1 + Model 2 test
case is largely done and verified; the exposure is now almost entirely (a)
the non-code deliverables (PPT + 2 demo videos), and (b) actually running
the live test case against the now-working sandbox to get a real accuracy
number — not missing features.
