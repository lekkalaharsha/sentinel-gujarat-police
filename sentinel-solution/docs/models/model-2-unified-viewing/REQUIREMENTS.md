# Model 2 — Requirements Coverage

Every bullet below is copied from the official challenge problem
statement's Model 2 section (`docs/hackathon/HACKATHON_DETAILS.md` §7),
then marked against real, verified code — not a self-assessment from
memory. Verified 2026-09-11, cross-checked against
`docs/hackathon/REQUIREMENTS_COVERAGE.md` §B.

Official spec text:

> Aggregates departmental feeds through a single interface without
> replacing existing infrastructure. Connects directly to departmental
> systems via RTSP/ONVIF/APIs — no middleware layer.

## Key functional features

| Requirement | Status | Evidence |
|---|---|---|
| Feed aggregation via RTSP/ONVIF/APIs | ✅ **Built, including real ONVIF discovery** | Direct RTSP `StreamManager` per camera, HLS-via-authenticated-proxy for the frontend (`routes_stream.py`); **ONVIF discovery is now real code**, not just a cited target — `streaming/onvif_discovery.py` implements WS-Discovery probe + Media `GetProfiles`/`GetStreamUri`, tried first when `SENTINEL_ONVIF_ENABLED=true` and falling back to the sandbox's direct-RTSP catalogue when no ONVIF device answers (the sandbox's own actual state — plain RTSP, no ONVIF endpoint, §13a). Verified against mocked WS-Discovery/SOAP exchanges (14 tests), not a live ONVIF device — no such device is reachable from this environment to test against for real |
| ANPR-based metadata generation | ✅ **Built, verified on real footage** | YOLOv8 detect → real trained `YoloPlateDetector` (YOLOv11) localizer → PaddleOCR → `PLATE_PATTERN` validation gate → `consensus_plate()` temporal fusion. A real car's plate (`GJ01RP6128`) read correctly 4/5 times on live sandbox footage, confirmed through the actual production accept-path at confidence 0.81 (`HLD.md` §3) — not a promising OCR string in isolation |
| Event tagging + camera-wise indexing | ✅ **Built** | `VehicleEvent` row per sighting: camera_id, plate, timestamp (`pts_ms`/`observed_at`), confidence, vehicle attributes, evidence crop — indexed and queryable by camera/plate/time |
| Searchable vehicle-movement records | ✅ **Built** | `GET /vehicle/{plate}/history` (full timeline, observed+inferred), `GET /vehicle/search-by-attributes` (color/type/etc.), `GET /vehicle/recent` |
| Configurable video walls | ✅ **Built** | `CameraGridView.jsx` — up to 9 simultaneous, independently-isolated live HLS tiles |
| Automated alerts | ✅ **Built** | Watchlist match → governed `Alert` lifecycle (new→acknowledged→resolved/dismissed); plus named anomaly alerts (wrong-way, stopped-in-restricted-zone via `analytics/anomaly.py`, opt-in per camera, built on existing motion/direction data) |

## Expected deliverables

| Deliverable | Status | Evidence |
|---|---|---|
| Unified viewer connecting ≥2 different systems | 🟡 **Partial** | The viewer architecture is system-agnostic (any RTSP/HLS source registered in Model 1's registry), but the live sandbox is one system with 30 cameras — "≥2 different systems" isn't literally demonstrated because only one sandbox exists to connect to. Not a code gap; see `IMPLEMENTATION_PLAN.md`. |
| ANPR demonstration | ✅ **Built, verified** | Same real-footage evidence as above; `demo_end_to_end.py` + `DEMO_SCRIPT_OWN_FEED.md` |
| Searchable metadata dashboard | ✅ **Built** | `VehicleIntelligence.jsx`/`SearchView.jsx`/`VehicleTimeline.jsx` — attribute search, movement timeline with explainability (`link_method`/`link_score`/`link_time_gap_s` surfaced in the UI) |
| Architecture note confirming departmental system independence | ✅ **Built** | `HLD.md` §3 — direct-connect, no middleware; existing VMS keep running unaffected |

## What's still honestly open

Only one 🟡: **"≥2 different systems."** This is a sandbox-availability
limit, not an unbuilt feature — the code path that would connect to a
second departmental VMS is identical to the one already connecting to the
first (a new catalogue entry + RTSP/HLS URL, no code change). It doesn't
block the mandatory live technical-evaluation test case (cross-camera
vehicle tracking within the one available sandbox, watchlist alerts, GIS
visualization) — those are all verified working. The related test-case
item "onboard ~50 heterogeneous cameras" (§C) is similarly 🟡: 30 real
cameras are onboarded and live, not 50, and the shortfall is sandbox
camera count, not onboarding-pipeline capacity (Model 1's bulk/API
onboarding already handles arbitrary count).

One architectural honesty note carried over from `ARCHITECTURE.md`: the
cross-camera identity-resolution embedding is a simpler HSV-histogram +
grayscale-template comparison, not a FastReID/OSNet deep embedding. It's
real and it's the stated differentiator (explainable link score, not a
black box), but it's a genuinely weaker signal than a production Re-ID
model — documented, not hidden. See `RESEARCH.md`.
