# Model 2 — Research Notes

Supporting research for `IMPLEMENTATION_PLAN.md`'s remaining items and
for justifying `ARCHITECTURE.md`'s stack deviations. Compiled 2026-09-11.
Cites real, checkable sources — no fabricated benchmarks.

## Cross-camera Re-ID: HSV-histogram vs. a real embedding model

Our current appearance-similarity signal (`analytics/tracker.py`-adjacent
code) is an HSV colour histogram + grayscale template compared by cosine
similarity. This is genuinely simple compared to production vehicle
re-identification:

- **FastReID** (JDAI-CV, Apache-2.0) and **OSNet** (Zhou et al., omni-scale
  network, originally for person Re-ID but widely adapted to vehicle
  Re-ID on VeRi-776/VehicleID) are the standard open-source deep-Re-ID
  baselines cited in `HLD.md`'s own documented upgrade path (§ future
  work, ~lines 732-737). Both need a labelled or at least large
  unlabelled vehicle-crop dataset to fine-tune meaningfully — something
  this sandbox doesn't have at volume (see below).
- **Why we didn't swap it in this pass:** `scripts/
  calibrate_embedding_threshold.py` (run 2026-09-10 against the real
  accumulated `sentinel.db`, 11,832 crops) found the *recall* side of
  Re-ID evaluation is genuinely blocked regardless of embedding choice —
  only 6 events have both a crop and a plate, 0 plates repeat across
  cameras in the real data, and only 4 identity links were ever
  plate-verified (not appearance-circular). A better embedding can't be
  validated without more cross-camera repeat sightings than the current
  30-camera/short-runtime sandbox produces. Swapping the embedding
  algorithm without the data to validate it would trade a known-simple,
  explainable signal for an equally-unvalidated "better-sounding" one —
  not a clear win under this repo's honesty rules. This is a genuine,
  documented limitation, not a schedule excuse.
- **Precedent for keeping it simple and explainable:** the `HLD.md` §1
  positioning explicitly does not claim novelty in ANPR/tracking itself
  (commercial systems — Staqu, Videonetics, Vehant, Innefu — already do
  ANPR+tracking at scale); the claimed differentiator is the
  **explainable** identity-resolution layer (`link_method`/`link_score`/
  `link_time_gap_s` per event), which a documented-but-simple signal
  supports just as well as an opaque deep embedding would, for a jury
  evaluation that can inspect the reasoning.

## ANPR OCR: PaddleOCR vs. alternatives

`STRATEGY.md` records that PaddleOCR was swapped in over an original
EasyOCR stub plan. PaddleOCR's multi-line-plate + homoglyph-correction
handling (added 2026-09-05, closing a real bug where two-line Indian
plates were read as garbage) is why it stayed — EasyOCR has no equivalent
built-in plate-layout awareness and would have needed the same
line-joining logic hand-rolled on top regardless. No further OCR
migration is recommended; the real remaining gap in the ANPR path is
**consensus voting**, not OCR engine choice, and that was already fixed
2026-09-10 (`consensus_plate()` position-weighted voting).

## Live viewing: HLS vs. WebRTC/WHEP

The suggested stack lists "WebRTC/HLS relay." We implement HLS-via-
authenticated-proxy only. WebRTC (via WHEP, the sandbox's advertised
protocol per `HACKATHON_DETAILS.md` §13a) gives sub-second glass-to-glass
latency versus HLS's typical 6–15s segment-buffer latency — a real
operational difference for a live police monitoring wall. This is a
genuine, documented gap (not built this pass): the sandbox exposes both
`cctv.corp8.cloud` (HLS/catalogue) and `103.250.160.189` (RTSP/WHEP) per
§13a, so WHEP is reachable in principle. Deferred because HLS already
satisfies the literal "unified viewer"/"video wall" deliverables and a
WHEP client adds a second live-video code path to maintain under time
pressure — see `IMPLEMENTATION_PLAN.md` for a scoped estimate if pursued.

## ONVIF Profile M and multi-vendor metadata interoperability

ONVIF Profile M (the metadata/analytics conformance profile — vehicle,
license-plate, face metadata) is the real vendor-neutral mechanism a
production Model 2 would use to receive metadata directly from
ONVIF-capable cameras instead of running our own YOLOv8/OCR pipeline on
raw video for every vendor. The sandbox doesn't expose ONVIF device
queries, so this isn't testable here, but it's the correct production
target — cross-referenced with Model 1's `onvif_profile` schema-extra
recommendation (`model-1-registry-gis/IMPLEMENTATION_PLAN.md` Part 2),
so a camera's registry entry could eventually indicate whether our own
pipeline is even necessary for that specific camera.

## Anomaly detection: precision caveat

`analytics/anomaly.py`'s wrong-way/stopped-in-restricted-zone detectors
use uncalibrated image-plane direction/speed (`direction_deg`,
`speed_px_per_s` on `VehicleEvent` are explicitly documented as
image-plane-only, not real-world units — no camera calibration/homography
is implemented). This is honest by design: the alerts are a real,
opt-in, per-camera signal built on genuinely-computed motion data, but a
"stopped" or "wrong-way" call is relative to the camera's own frame, not
a calibrated ground-plane measurement. Calibrating this per-camera
(homography from known reference points) is a real Model 2 hardening
item if pursued at scale — not attempted this pass, no fabricated
precision numbers exist for it.
