# Sentinel — High-Level Design

**Submission deliverable per HACKATHON_DETAILS.md §9.2.** This document
describes the architecture actually implemented in `sentinel-solution/`
(verified against real runtime execution, not just design intent — see
"Verification status" callouts throughout) plus the documented production
path for scaling it to the full ~80,000-camera, 26-department target.
Architecture rationale and IN/OUT scoping decisions are recorded in
`STRATEGY.md`; this document is the submission-facing HLD derived from it.

## 1. Solution model and justification

**Hybrid architecture: Model 1 (Centralised CCTV Registry & GIS Mapping) —
mandatory base — combined with Model 2 (Unified Viewing & Metadata
Analytics), with a documented Model 3/4 (VMS federation → central AI
platform) evolution path for statewide scale-out.**

This is a hybrid in the sense the problem statement defines
(HACKATHON_DETAILS.md §7: "combine elements from two or more models"), and
"innovative hybrid/customized architecture with operational value" is an
explicit bonus criterion (§10). We claim hybrid credit only for what is
genuinely built (Model 1 + Model 2, verified end-to-end — see §5/§9); the
Model 3/4 elements are presented as the documented production roadmap (§2,
§7), **not** claimed as implemented. Building a real per-vendor VMS
federation bus (Model 3) is deliberately out of scope for the build window
(see STRATEGY.md's OUT list) — claiming it as built would be exactly the
kind of overstatement this submission avoids.

Justification: Gujarat already operates VISWAS/NETRAM/TRINETRA at scale
(7,000+ cameras, Phase-II adding ~10,500 more). Pitching a from-scratch
centralized VMS (Model 4) invites the reasonable jury question "what did
you invent that doesn't already exist?" Model 2's direct-connection
approach — no new middleware layer, connect straight to each department's
RTSP/ONVIF/API surface — is both what the problem statement recommends for
teams that don't want to build a federation bus (Model 3) and the most
achievable, honestly-scoped target in the build window. The Model 1 base
is what makes it more than a point solution: it's the common registry/GIS/
governance index every other model sits on top of (§7 of the problem
statement), and it's what a Model 3/4 evolution would extend rather than
replace. See `STRATEGY.md` §"The pitch correction" for the full framing.

**What is and isn't claimed as the invention (honest differentiation).**
Detection, ANPR, and cross-camera vehicle tracking are already shipped
commercially in India — by Staqu (JARVIS), Videonetics, Vehant, and Innefu,
among others (see `../RESEARCH_EXISTING_SYSTEMS.md` §7). This submission does
**not** claim to have invented those, and would lose credibility with a
jury that knows these vendors if it did. Sentinel's specific contribution is
the **open, explainable vehicle-identity-resolution layer**: a persistent
vehicle entity assembled from *uncertain* observations — plate-OCR
confidence, appearance similarity, temporal feasibility, and recency — where
every cross-camera link records *why* it was made
(`link_method`/`link_score`/`link_time_gap_s`, §6), and where an unreadable
plate degrades gracefully to attribute/appearance tracking rather than
dropping the vehicle (§5). The entity-plus-observations-with-explainable-links
shape is a lightweight, open-source realization of the pattern intelligence
platforms like Palantir Gotham use (Object ↔ Track ↔ Observation), applied
narrowly to vehicles — not a claim to match those platforms' scope.

## 2. Architecture overview

```
26 Departments (incl. existing VMS/TRINETRA/NETRAM)
        │  ONVIF / RTSP / API
        ▼
┌─────────────────────────────────────────────────────────────┐
│ SENTINEL — pilot/edge tier (this submission, ~30-camera scale)│
│                                                                │
│  Catalogue client ──polls──▶ cameras.json (camera discovery)  │
│         │                                                      │
│         ▼                                                      │
│  Stream Manager ──opens/closes──▶ RTSP workers (1 per camera) │
│         │  PTS-driven, TCP-forced, backoff reconnect           │
│         ▼                                                      │
│  Analytics Pipeline (sampled frames, stride-N):                │
│    detect (YOLOv8) → plate region → enhance → OCR (PaddleOCR)  │
│      → within-camera tracker (temporal plate fusion)           │
│      → appearance embedding (Re-ID)                            │
│      → cross-camera identity resolution                        │
│         │                                                      │
│         ▼                                                      │
│  Event store (PostgreSQL-compatible via SQLAlchemy, SQLite     │
│  in dev): VehicleEvent, VehicleIdentity, CameraRegistry,        │
│  WatchlistEntry, Alert, AuditLog, ApiKeyEntry (RBAC)            │
│         │                                                      │
│         ├──▶ Watchlist engine → real-time alerts                │
│         ├──▶ Purpose-bound, audited vehicle-history API         │
│         └──▶ RBAC-gated REST API (FastAPI)                      │
│                     │                                          │
│                     ▼                                          │
│              React frontend: GIS map, live HLS view,           │
│              movement timeline + explainability, watchlist,    │
│              gap-analysis / onboarding ops console              │
└─────────────────────────────────────────────────────────────┘
```

**Documented production target** (not built this week — see §7 and
STRATEGY.md's OUT list): a regional media fabric (MediaMTX/go2rtc) and an
event bus (Kafka) sit between the per-department connectors and the AI
fabric, so ingestion scales horizontally without every analytics worker
holding its own RTSP socket per camera.

**Core principle stated explicitly, not glossed over:** centralize
metadata/events/identity/GIS/governance — not every raw video frame.
80,000 cameras × ~2 Mbps ≈ 160 Gbps sustained, ~1.7 PB/day. Full central
raw-video ingestion is not a credible target for any team at this budget,
and we say so rather than implying otherwise. See §7 for the actual scaling
strategy (edge inference, selective video egress).

## 3. Heterogeneous camera / VMS integration approach

- **Discovery, never hardcoding:** every camera URL is derived from the
  live catalogue (`GET /api/ingest` generically, `cameras.json` for this
  specific sandbox) — camera IDs and availability can change; the
  catalogue is the contract (`catalogue.py`).
- **Protocol handling:** RTSP forced over TCP
  (`OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp`); mixed H.264/H.265
  streams tolerated (decoder warnings at join are logged, not fatal).
- **Timing correctness:** every frame carries `pts_ms` from
  `CAP_PROP_POS_MSEC`; `CAP_PROP_FPS` is never trusted. Downstream
  tracking/velocity math uses PTS deltas, never wall-clock arrival time —
  required because the gateway replays a buffered GOP on connect, which
  arrives faster than real time.
- **Resilience:** exponential-backoff reconnect (2s → 30s cap), never a
  tight loop; a scene discontinuity (the sandbox's recording loop point,
  detected as PTS going backward) triggers an explicit state reset in the
  tracker rather than silently producing garbage across the cut.
- **Heterogeneous departments:** `CameraRegistry.department` plus the
  onboarding API (`POST /cameras`, `POST /cameras/bulk`) let a camera be
  tagged by owning department independent of protocol/vendor — the
  registry's job is to be the common index Models 2/3/4 all sit on top of,
  per HACKATHON_DETAILS.md §7's note that Model 1 underlies the others.
- **ONVIF as the device-abstraction standard:** the vendor-neutral
  integration surface targets ONVIF Profile S/T (the standard both Genetec
  Security Center and Milestone XProtect — 10,000+ device models — build
  their multi-vendor support on; see `../RESEARCH_EXISTING_SYSTEMS.md` §2).
  The sandbox exposes plain RTSP, so the pilot connects directly; ONVIF is
  the documented onboarding path for real heterogeneous department cameras.

- **Cross-camera timing doesn't depend on camera clocks:** within a
  camera, timing uses PTS deltas (never wall-clock — required for
  correct velocity/dwell math, see above). But cross-camera correlation
  (travel-time plausibility between two different cameras' sightings)
  cannot use each camera's own clock — 80,000 legacy cameras have no
  guaranteed NTP sync, and assuming otherwise would be exactly the kind
  of unstated dependency a technical jury would catch. Instead,
  `VehicleEvent.observed_at` is stamped once, by the single analytics
  server's own clock, at the moment each event is persisted
  (`db/models.py`) — one time authority for cross-camera ordering,
  independent of any individual camera's internal clock accuracy.

**Verification status:** the RTSP pipeline was validated against the real
sandbox `cam01` feed in an earlier working session (per prior scoped
credentials). **That validation could not be re-confirmed as part of this
document's writing** — the sandbox access token is not currently configured
in this environment. Re-confirm against a live feed before relying on this
claim in the live demo; do not present it as currently-verified without
doing so.

## 4. Live stream ingestion / processing / management

Per-camera architecture: one `RtspCameraWorker` thread per live camera,
managed by `StreamManager`, which reconciles against the catalogue on an
interval — opening workers for newly-live cameras, closing workers for
cameras no longer in the catalogue ("pace your load": only open what's
being processed).

Frame sampling: `ANALYTICS_FRAME_STRIDE` (default every 5th frame) bounds
inference cost per camera; frame rate and resolution differ per camera and
are read from catalogue metadata, not assumed uniform.

**Camera health monitoring** (Model 1 deliverable): each worker exposes
`connected` + `last_frame_at`; a periodic sync loop writes this into
`CameraRegistry.is_healthy` / `last_seen_live_at`. A camera that has never
been confirmed live reports health as `null` (unknown), not a false
"healthy" default — an onboarded-but-never-connected camera must not look
identical to a confirmed-working one.

## 5. AI video analytics approach

```
frame → vehicle detection → plate region → enhancement → OCR
      → within-camera temporal fusion (majority-vote across sampled frames)
      → appearance embedding
      → cross-camera identity resolution (plate-first, appearance-second)
      → persist → watchlist check
```

| Stage | Implementation | Status |
|---|---|---|
| Vehicle detection | YOLOv8n (`ultralytics`, pretrained COCO weights) | **Real, verified** against a real photo (car/truck/bus/motorcycle/person classes need no fine-tuning) |
| Plate localization | Heuristic crop (lower-middle third of vehicle bbox) | Working substitute; no fine-tuned Indian-plate localizer available in the build window — documented gap, not hidden |
| Plate enhancement | Grayscale + CLAHE + upscale | **Real**, dependency-free, measurably improves OCR hit rate on small crops |
| OCR | PaddleOCR (pinned 2.9.1 — see §8 for why the pin matters) | **Real, verified** end-to-end including the genuine-failure path (blank plate → `None`, not a crash) |
| Within-camera tracking | Real ByteTrack (`ultralytics` `model.track(tracker="bytetrack.yaml")`, one persistent tracker instance per camera) | **Real, verified** — Kalman-filter-based association via a library already in our dependency tree, not a new model; IOU-overlap fallback retained for detections ByteTrack hasn't confirmed yet, or the stub detector path |
| Appearance Re-ID | HSV colour histogram + grayscale template, cosine similarity | **Real, working**, not state-of-the-art (FastReID/OSNet is the documented upgrade path) |
| Cross-camera identity | Plate-first, appearance-second resolver | **Real, verified end-to-end**: an anonymous (unreadable-plate) sighting at camera A correctly upgrades to a plate identity retroactively the moment ANY camera reads it |
| Make/model classification | Not implemented | Honest gap — no open-source model classifies Indian-market vehicle make/model well; returns `None` rather than a fabricated guess |
| Motion attributes (dwell / speed / direction) | Derived from track bbox path over PTS | **Real, verified** — image-plane metrics (px/s, screen-direction), NOT calibrated km/h; enables dwell/wrong-way/stopped-zone filters. Inspired by BriefCam's searchable attributes (`../RESEARCH_EXISTING_SYSTEMS.md` §3) |
| Low-confidence read suppression | Config threshold on fused plate confidence | **Real, verified** — a shaky read is withheld (vehicle still logged anonymously) rather than spawning a false identity/alert. Inspired by Flock (`../RESEARCH_EXISTING_SYSTEMS.md` §1) |
| Geo-temporal route reconstruction | Haversine distance between camera GPS + time-gap → plausibility check; OBSERVED sightings interleaved with honestly-labelled INFERRED camera-less segments (`analytics/geo.py`) | **Real, verified** — the differentiator layer for the "advanced cross-camera correlation" bonus (§10 of the problem statement). Straight-line/lower-bound only; a *high* implied speed flags "not a direct drive" (unmonitored detour / possibly different vehicle). Full road-network (OSM) routing + forward next-camera prediction are documented roadmap, not built — see below |

**"ANPR failure ≠ tracking failure"** is the core design principle (see
STRATEGY.md and `sentinel-solution/README.md`): a vehicle is never dropped
just because a plate can't be read on a given camera. It's logged by
colour/type/dimensions/appearance embedding, and the appearance signal
carries identity across cameras until a plate read resolves it. Verified
with a real (non-mocked) three-camera scenario: two unreadable plates, one
successful read, all three sightings correctly merge into one identity.

**Real-world accuracy caveat, stated plainly:** OCR accuracy has been
verified against clean synthetic plate text (>99% confidence) and against
a real photo for vehicle detection — not yet against real Indian-plate
photography (motion blur, oblique angles, non-standard fonts/spacing,
actual government camera image quality). This is the single most
jury-visible number on evaluation day and is currently unmeasured against
real footage. Accuracy in production comes from the detector + regex
plate-pattern validation + temporal fusion across frames working together,
not the OCR engine in isolation.

**Vendor-claimed vs. field accuracy — a documented real-world gap, cited
not assumed:** Re-ID/ANPR benchmark accuracy on lab datasets (Market-1501,
DukeMTMC: 90%+) does not transfer directly to field deployment. The
clearest recent evidence: Flock Safety — a commercial ANPR network
advertising "high-90s" accuracy — was found by Roseville, CA police to
have misread **71% of the 1,427 stolen/felony-vehicle alerts** it
generated in 2023–24, largely attributed to camera placement/angle rather
than the model itself ([Business Insider via Gizmodo, Aug 2026](https://gizmodo.com/flock-cameras-got-the-wrong-license-plate-71-of-the-time-in-california-city-2000793483);
[Davis Vanguard, Aug 2026](https://davisvanguard.org/2026/08/roseville-police-ai-camera-errors/)).
The lesson taken here is not a specific accuracy number for *this* system
(unmeasured — stated above) but the *mechanism*: field conditions
(camera angle, distance, placement) degrade accuracy far more than model
choice does, and a system must be designed to fail safely when that
happens. That is precisely why Re-ID here is a *secondary confirmation
signal*, plate-first (§6), and why low-confidence plate reads are
suppressed rather than promoted to alerts (§5 table, "Low-confidence read
suppression") — a partial or uncertain read is never allowed to fan out
into "hundreds of matching vehicles"; it stays an anonymous,
attribute-tracked sighting instead.

## 6. CCTV-to-watchlist correlation and alert methodology

Every persisted `VehicleEvent` with a resolved plate is checked against
`WatchlistEntry` (stolen/wanted/blacklisted) at write time
(`watchlist/service.py`). A match creates an `Alert` row immediately —
polled by the frontend's Alerts panel every 5 seconds.

**Governed alert lifecycle (entity-lifecycle pattern, Palantir-inspired —
see `../COMPETITIVE_TEARDOWN.md`).** An alert is not a fire-and-forget log
line; it's a live investigation item with an enforced state machine:
`new → acknowledged → resolved`, with `dismissed` (false positive)
reachable from `new`/`acknowledged`. Only transitions declared in
`ALERT_TRANSITIONS` (`db/models.py`) are permitted — the API rejects an
illegal move with 409 and an unknown state with 400, and the frontend only
renders the transitions the server reports as legal, so the governance rule
lives in exactly one place. Each transition records **who** made it and
**when** (`status_updated_by`/`status_updated_at`), mirroring the
purpose-bound audit ethos. `dismissed` being a first-class, auditable
terminal is deliberate: marking an AI hit as a false positive is the
concrete expression of "AI output is a lead, not evidence" (§6 above) —
a recorded human decision, not silence. Verified end-to-end through the
real HTTP routes with auth (legal walk, rejected illegal transitions,
accountability trail, false-positive path, and backward-compatible
`/ack`). The legacy `acknowledged` boolean is kept in sync so nothing that
consumed the old shape breaks.

**Government-DB integration targets:** the watchlist is the local
cross-reference; the production integration targets are Gujarat's own law-
enforcement databases named in HACKATHON_DETAILS.md §8 — **VAHAN** (vehicle
registration), **SARTHI** (licensing), **eGujCop** and **CCTNS** (Crime &
Criminal Tracking Network & Systems, the national criminal DB that Indian
ICCCs already integrate with — see `../RESEARCH_EXISTING_SYSTEMS.md` §5).
The design principle is **query, don't copy**: Sentinel queries these
systems for a match on demand rather than replicating their data, keeping
it an interoperability layer rather than a shadow database.

**"Why was this vehicle linked?" explainability** (bonus-relevant,
demoable): every `VehicleEvent` records `link_method` (new identity / plate
continuation / plate upgrade / appearance match), `link_score` (cosine
similarity, when appearance carried the link), and `link_time_gap_s`
(seconds since the identity's previous sighting) — captured at the moment
of the resolution decision in `identity.py`, because it cannot be
reconstructed afterward (`VehicleIdentity` only retains its *latest*
embedding). The frontend renders these as a fused, heuristically-weighted
score (plate confidence 50% / appearance similarity 35% / recency 15%) —
explicitly labeled a transparency aid, not a calibrated probability.

**Known failure mode, stated rather than hidden:** an appearance-only link
(no plate confirmation on either end) can be wrong — two vehicles of the
same make/colour genuinely look alike to a colour-histogram embedding.
This is exactly why an appearance-only `link_method` is surfaced
differently from a plate-confirmed one in the explainability panel, and
why the system's policy (below) treats appearance-only links as leads for
an analyst to review, never as a standalone basis for field action.

**Operational policy — AI output is a lead, not evidence:** no route in
this system auto-dispatches an officer or auto-confirms an identity. Every
watchlist hit lands in the Alerts panel for human acknowledgement
(`routes_alerts.py`); every vehicle-history/search result carries its
`link_score` so an investigator sees *why* the system linked a sighting,
not just that it did. This is also the concrete mitigation for
**automation bias** (an operator rubber-stamping a high-volume alert feed
without scrutiny): low-confidence links are visually distinguished, not
buried at the same weight as a plate-confirmed one, so the operator's
attention is drawn to exactly the cases that need it.

## 7. Scalability toward ~80,000 cameras

See the standalone `SCALABILITY.md` for the full plan-for-scale deliverable
(compute sizing, storage tiers, bandwidth math, cost estimate, HA/DR). This
HLD states the architectural shape only:

- **Edge inference, not central raw video.** Detection/OCR/tracking run
  near the camera (regional edge compute), emitting only structured events
  (plate, timestamp, camera, embedding vector) to the central plane —
  matches the ~160 Gbps / ~1.7 PB/day math that rules out full central
  video ingestion.
- **Horizontal scaling by adding stream-manager instances**, each owning a
  shard of cameras, publishing events to a shared bus (Kafka/RabbitMQ —
  documented, not deployed this week) rather than one process holding
  every RTSP socket.
- **PostgreSQL + PostGIS** (SQLite in this dev build, swappable via
  `DATABASE_URL` since all access goes through SQLAlchemy) for the event/
  registry/identity store at production scale, partitioned by time and
  region.
- **RBAC is designed to extend, not rebuild:** the current API-key + role
  model (`api/auth.py`) maps directly onto department-scoped roles at
  scale — `ApiKeyEntry.department` already exists for this.

## 8. Technologies, frameworks, tools

FastAPI, SQLAlchemy (PostgreSQL-ready), OpenCV, YOLOv8 (`ultralytics`),
PaddleOCR 2.9.1 (pinned — **PaddleOCR ≥3.0 changed its public API in a way
that breaks this project's OCR wrapper; verified by installing 3.7.0 and
hitting the incompatibility at runtime**, not assumed), React, Leaflet,
hls.js. All open source, per the hackathon's Open Source Requirement.

**Operational note verified this build:** on Windows, constructing the
YOLOv8 (torch-backed) detector before the PaddleOCR (paddle-backed) reader
in the same process is required — the reverse order corrupts torch's
native DLL loading. Documented and enforced in `main.py`; only verified on
Windows, not yet on the likely-Linux production/demo box.

## 9. Security, privacy, RBAC

- **RBAC is real, not a stub:** every API route requires an
  `X-Sentinel-API-Key` header mapping to a role (`viewer` / `investigator`
  / `admin`) via `api/auth.py`. A request without a valid key is rejected
  (401/403), not logged-and-allowed. This is a genuine, if minimal (no
  full OAuth/session flow — an honest scope choice for the build window),
  implementation of Model 1's explicit "department-wise RBAC" deliverable.
- **Purpose-bound, audited queries:** every vehicle-history/search query
  logs the *authenticated* user (from the API key, not a self-reported
  string), stated purpose, and optional case ID to `AuditLog` — this
  closes a real gap found during this build: an earlier version trusted a
  client-supplied `user_id` string, which made the audit trail spoofable.
- **Enforced data retention (DPDP storage limitation):** vehicle events,
  identities, and alerts are automatically purged after a configurable
  window (`db/retention.py`, default 30 days pilot); **audit logs are kept
  longer** (default 365 days) so the accountability trail outlives the
  personal data it describes. Modelled on the UK National ANPR system's
  enforced 12-month schedule — and on the *criticism* that system drew for
  lacking enforced oversight (see `../RESEARCH_EXISTING_SYSTEMS.md` §6):
  we enforce retention in code, not policy-on-paper. Admins can view the
  policy (`GET /admin/retention-policy`) and trigger a purge on demand
  (`POST /admin/purge`) so the control is demonstrable, not just claimed.
  Known gap, stated: per-case evidential retention exemption (CPIA-style)
  is not built — export to a case file before data ages out.
- **DPDP posture:** Section 17 of the DPDP Act 2023 exempts law-enforcement
  processing, but this system is designed as if the Act's substantive
  obligations apply anyway — purpose limitation, audit logging, retention
  limits (above), and data minimization (attribute-only fallback instead of
  storing raw video) are all load-bearing design choices, not decoration.
- **Purpose limitation, enforced not just stated:** every deployment is
  configured for a stated use case (e.g. vehicle-tracking for an active
  case), and every history/search query requires a `purpose` string that
  is itself audit-logged (§9 above, `AuditLog`) — the system does not
  expose a generic "browse all camera activity" capability; querying
  requires a plate, a case, or a watchlist match to start from.
- **Right to erasure / breach notification, stated honestly as unbuilt:**
  the DPDP Act's erasure and breach-notification obligations are not yet
  implemented as self-service flows (no "request my data be deleted" API,
  no breach-notification pipeline). Retention enforcement (`db/retention.py`)
  is the mechanism that would carry this — a purge trigger and an admin
  notification hook are the concrete next steps, not built this week.
- **Bias evaluation:** no demographic-parity testing has been run against
  the detector/Re-ID models — there is no vetted Indian demographic
  benchmark available in the build window to run it against honestly.
  Stated as a pre-deployment requirement, not deferred silently: models
  should be evaluated for performance parity across vehicle types/regions
  before operational use, with periodic re-audits as the fleet/dataset
  changes.
- **Anticipated adversarial framing, addressed directly:** a privacy
  advocate's strongest objection is that attribute + appearance tracking
  is "facial recognition without the face" — a movement record built
  without individual consent. The honest answer is not that this concern
  is wrong, but that the design deliberately narrows it: no face
  embeddings are computed or stored (§5, `attributes.py` returns no
  face/identity biometric), every query is purpose-bound and audited
  (this section), retention is enforced in code with a short default
  window (30 days) rather than promised in policy, and the system
  explicitly does not claim to identify who someone *is* — only what
  vehicle was seen where, which is the narrower, DPDP-Section-17-scoped
  claim this proposal makes throughout.
- **Security frameworks:** the design aligns with NIST Cybersecurity
  Framework and CISA Secure-by-Design principles (the same frameworks
  commercial ANPR networks like Flock cite) — hashed credentials,
  least-privilege RBAC, audit logging, and input validation (the SSRF fix
  below) are the concrete expressions of that alignment, not a compliance
  checkbox.
- **Found and fixed during this build, not shipped:** an SSRF vulnerability
  in the HLS proxy (`routes_stream.py`) where a client-controlled segment
  URL could make the backend fetch arbitrary hosts using the sandbox's
  authenticated session — closed with a same-host validation check,
  verified against both the attack case (rejected) and the legitimate
  same-host case (still works).
- **API keys are stored hashed** (SHA-256), never in plaintext, so a
  database leak doesn't hand out working credentials.

## 10. Known gaps (stated, not hidden)

- WHEP (low-latency WebRTC live preview) is not implemented — HLS via an
  authenticated backend proxy is the working live-view path.
- ByteTrack (ai fabric bonus criterion) **is now implemented** via
  Ultralytics' built-in tracker (`model.track(..., tracker="bytetrack.yaml")`),
  one persistent instance per camera — verified end-to-end (stable track
  IDs across repeated frames, correct per-camera isolation, correct reset
  on scene discontinuity; see commit history). The custom IOU-overlap
  tracker remains as the fallback when no external track_id is available.
  Not yet tuned: ByteTrack's `track_buffer` (default ~30 calls) counts
  *sampled* frames (every `ANALYTICS_FRAME_STRIDE`th), not raw frames or
  elapsed time, so its occlusion-tolerance window is decoupled from real
  time in a way the PTS-driven `TRACK_TIMEOUT_MS` elsewhere in the pipeline
  is not — worth revisiting if occlusion handling needs tuning against
  real footage.
- Real Indian-plate OCR accuracy is unvalidated against actual government
  footage (see §5).
- GIS coordinates for real sandbox cameras are not auto-populated — the
  catalogue doesn't return them; `scripts/onboard_from_catalogue.py`
  infers department by keyword-matching camera names as a starting point,
  explicitly flagged as needing manual review, not verified ground truth.
- Sandbox RTSP validation could not be reconfirmed while writing this
  document (see §3) — reconfirm before the live demo.
- Legacy-fleet credential management (vendor password rotation, mixed
  Basic/Digest/proprietary-token auth across 26 departments' real cameras)
  is not addressed — this pilot connects to one sandbox with one access
  token. Real onboarding needs a per-camera/per-department credential
  store with rotation support; not designed or built this week.
- Re-ID similarity search at full scale (matching one query embedding
  against a historical store spanning 80,000 cameras) is not a solved
  problem here or in the wider Re-ID literature — see `SCALABILITY.md`
  §2 for the documented approach (candidate filtering before similarity
  search, not a brute-force global nearest-neighbor scan).
- **Geo-temporal layer — road-network routing + predictive pruning are
  roadmap, not built.** What's built (`analytics/geo.py`) is straight-line
  (haversine) distance + time feasibility for the INFERRED route segments —
  honest and dependency-free. NOT built: (a) true road-network / OSM
  travel-time (OSM coverage of Gujarat's minor roads is incomplete — an
  external-data dependency, documented rather than faked), and (b) forward
  "PREDICTED next-camera" candidate pruning to constrain the expensive
  cross-camera match. At the ~50-camera pilot, pruning saves nothing
  observable (brute-force is instant); its value is the 80k scalability
  story (`SCALABILITY.md` §2's candidate-filter-before-vector-search). If
  built, pruning must be a soft ranking hint, never a hard exclusion, and
  must never override a confirmed plate read — a false negative (losing the
  vehicle) is worse than extra compute for a police tool.
- **Fine-tuned plate localizer — evaluated, deliberately not integrated.**
  `morsetechlab/yolov11-license-plate-detection` (Hugging Face) is a real,
  named-publisher YOLOv11 plate detector shipping both `.pt` and ONNX
  weights — ONNX avoids the arbitrary-code-execution risk of loading an
  unvetted `.pt` file, which is why an earlier candidate from a
  single-contributor repo was rejected. This one is licensed **AGPL-3.0**,
  a copyleft license whose network-use clause has real implications for a
  government backend and was not something to accept without an explicit
  decision — deferred pending that call, not integrated. Its own model
  card also discloses train/test contamination in its reported accuracy,
  so the number (mAP@50 0.98) is stated by the publisher as unreliable.
- **IISc UVH-26 — a stronger Indian-specific detector, evaluated, not
  swapped in.** AI for Integrated Mobility @ IISc released `iisc-aim/UVH-26`
  (Hugging Face): YOLOv11-S/X, RT-DETRv2-S/X, and DAMO-YOLO-T/L weights
  trained on 26,646 real Indian urban-traffic images (~2,800 Bengaluru
  Safe-City cameras, 1.8M boxes, 14 Indian vehicle classes), backed by an
  arXiv technical report (2511.02563). Reports up to 31.5% higher mAP than
  COCO-pretrained baselines on their own benchmark — a relative figure
  under their evaluation, not a claim about accuracy on our footage. This
  is real, institutionally credible, and directly relevant (our current
  detector is COCO-pretrained YOLOv8n, not Indian-traffic-specific). Not
  swapped in this build: doing so properly means re-validating detection
  end-to-end against real footage before trusting it in front of a jury,
  which this build window didn't have room for after the ByteTrack work
  above. Documented as the strongest available upgrade path for the
  detector stage specifically.
- **FastReID — the documented Re-ID upgrade, unchanged assessment.**
  `JDAI-CV/fast-reid` (GitHub) is a real, mature Re-ID research framework
  covering vehicle Re-ID specifically, confirmed still the right target if
  `ColorHistogramEncoder` (`reid.py`) needs to be replaced — consistent
  with what STRATEGY.md already named before this research pass. Hugging
  Face's own vehicle-Re-ID model listings are sparse and not vetted enough
  to trust over a maintained framework — a single downloaded checkpoint
  from an unvalidated source was correctly not treated as a shortcut here.
- **VLM-based OCR — noted as a production alternative, not attempted.**
  General-purpose vision-language models (Qwen2.5-VL, LLaVA, moondream —
  run locally via Ollama or similar) can perform plate OCR as a byproduct
  of broader visual understanding, and are reportedly more robust to
  font/script variation than a fine-tuned CNN — potentially relevant given
  Indian plates' format diversity. Not pursued this build: it requires
  standing up a new local-LLM-serving runtime competing with YOLO/PaddleOCR
  for the same GPU, adding latency and a new infrastructure dependency —
  exactly the kind of new architectural layer out of scope for this
  window (see STRATEGY.md).

## 11. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Real Indian-plate OCR accuracy is materially worse than synthetic-test results | High | High — undermines the core demo claim | Temporal fusion + regex validation + low-confidence suppression already reduce reliance on any single read (§5); re-test against real sandbox footage before the live demo, not after |
| Appearance-only Re-ID false match (two similar vehicles) | Medium-High | Medium — wrong lead, not wrong action | Plate-first resolution, appearance as secondary signal only, explainability panel flags appearance-only links distinctly (§6) |
| Sandbox access token unavailable/expired before the demo | Medium | High — blocks live verification entirely | Confirm access early, not on demo day; stub fallback path already exists and runs (loud warning, no fabricated detections) if it fails |
| Operator alert fatigue / automation bias on a live feed | Medium | Medium — undermines the human-in-the-loop safeguard's real value | Low-confidence links visually distinguished, not equal-weighted with confirmed ones (§6); no route auto-dispatches on a match |
| Windows-specific torch/paddle DLL conflict resurfaces on the demo machine | Low-Medium | High — blocks the whole pipeline from starting | Load order is enforced in `main.py` and documented (§8); verify on the actual demo hardware beforehand, not assumed from dev-machine success |
| Jury asks for a cost/scale number not in this document | Low | Medium — looks unprepared live | `SCALABILITY.md` covers GPU sizing, bandwidth, storage, and rollout cost — reference it directly in the presentation, don't re-derive live |
| Real camera GIS/department metadata from `onboard_from_catalogue.py` is wrong when finally run against the live sandbox | Medium | Low-Medium — cosmetic on the map, not a pipeline failure | Script output is explicitly flagged as needing manual review (README), not trusted as ground truth by default |
