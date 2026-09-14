# Model 2 — Implementation Plan

Concrete remaining work only — this model is already built and verified
against real sandbox footage; nothing here is a rebuild. Unlike Model 1,
Model 2 has **no required-tier gaps against the literal spec text** — the
one 🟡 in `REQUIREMENTS.md` ("≥2 different systems") is a sandbox-
availability limit, not missing code. Everything below is Part
2-equivalent: research-derived hardening, useful if time allows, not a
submission blocker.

## Done

- **"Unified viewer connecting ≥2 different systems" — built and
  live-verified 2026-09-13.** **Qualified 2026-09-11** (an independent
  project review found the original "zero code change" claim overstated):
  a genuinely different real system needs a new adapter, exactly like
  Model 3's `VMSAdapter` pattern — proven by ONVIF discovery needing a
  new ~250-line module. That adapter-sized change is exactly what was
  built for System B: `app/external_camera_source.py` (~130 lines) polls
  Caltrans District 3's real, public, unauthenticated CCTV API and
  upserts into `CameraRegistry` with `source_system="caltrans_d3_public_api"`,
  registry-only (never touches `catalogue.py`, so `StreamManager`/the
  ANPR pipeline can never mistake it for an RTSP-analyzable Gujarat
  camera). Frontend: `SnapshotView.jsx` renders it as a periodically-
  refreshed still image with an explicit "EXTERNAL SOURCE — periodic
  snapshot, not live video" badge inside the same `CameraGridView` used
  for live sandbox tiles — one unified viewer, two genuinely independent
  systems, each honestly labelled by real feed type. 4 new regression
  tests (`tests/test_external_camera_source.py`); live-verified against
  the real endpoint (13s round trip for the full ~850KB district payload
  — `fetch_raw`'s timeout was bumped from 10s to 30s after this was found
  failing against real latency, not a fixture). Off by default
  (`SENTINEL_EXTERNAL_CAMERA_SOURCE_ENABLED=false`) since it's a real
  outbound network call — must not fire implicitly in tests or a plain
  `python -m app.main` run; enable it for the demo recording. This was
  not a fake/relabeled second source — see the "don't simulate a fake
  second system" note this replaced.
- **"Onboard ~50 heterogeneous cameras."** Same reasoning — Model 1's
  bulk/API onboarding handles arbitrary camera count already; 30 is the
  sandbox's real ceiling, not ours.

## Part 1 — worth doing if time allows (hardens a real, documented gap)

### M2-1 — WHEP live-view path (see `RESEARCH.md`)

- [ ] **Add a WHEP client alongside the existing HLS proxy**, selectable
      per camera or as a live-view toggle, targeting sub-second latency
      versus HLS's 6–15s segment buffer. The sandbox already exposes WHEP
      at `103.250.160.189` per `HACKATHON_DETAILS.md` §13a. Effort:
      ~4–6 hrs (new backend proxy/signalling route mirroring
      `routes_stream.py`'s auth pattern, frontend `<video>`+WebRTC
      peer-connection component). **Risk:** a second live-video code path
      to keep working under the same PTS/backoff/reconnect discipline as
      the RTSP workers — don't half-build this if there isn't time to
      also verify it against real sandbox WHEP endpoints.

### M2-2 — Per-camera homography calibration for anomaly detection

- [ ] **Calibrate `direction_deg`/`speed_px_per_s` to real-world units**
      via a one-time per-camera homography (4 reference points → ground
      plane), so wrong-way/stopped-in-restricted-zone alerts carry a real
      speed estimate instead of an image-plane-relative one. Effort:
      ~3–4 hrs (one calibration helper + a per-camera calibration record,
      likely a new nullable JSON column on `CameraRegistry` or a small
      new table — needs an additive migration either way). **Needs
      real-world reference measurements per camera to be honest** —
      don't fabricate calibration points for cameras never physically
      surveyed; leave uncalibrated cameras reporting image-plane values
      as today, just gate the "real-world speed" claim on calibration
      being present.

### M2-3 — ONVIF Profile M readiness note (docs-only, no code)

- [ ] **Cross-link to Model 1's `onvif_profile` field** (proposed in
      `model-1-registry-gis/IMPLEMENTATION_PLAN.md` Part 2) once/if that
      field ships — a camera whose registry entry says Profile M could,
      in a production deployment, skip our own YOLOv8/OCR pipeline
      entirely and consume vendor-native metadata instead. No code today;
      this is a roadmap note for `HLD.md`'s production-path section, not
      a build item this hackathon.

### M2-4 — ONVIF discovery (Profile S device discovery + stream URIs) — done

- [x] **Real WS-Discovery + Media `GetProfiles`/`GetStreamUri` implemented**
      in `streaming/onvif_discovery.py`, wired into `catalogue.py`'s
      `CatalogueClient.refresh()` as an ONVIF-first, sandbox-catalogue-
      fallback (`SENTINEL_ONVIF_ENABLED`, default `false` since the
      sandbox has nothing to discover). 14 new tests
      (`tests/test_onvif_discovery.py`) cover probe parsing, the
      GetCapabilities→GetProfiles→GetStreamUri handshake, per-device
      failure isolation, and the catalogue fallback wiring, all against
      mocked WS-Discovery/SOAP responses — full backend suite 84/84
      passing after this change. **Honestly unverified against a live
      ONVIF-conformant camera** — none is reachable from this environment
      or the hackathon sandbox (§13a: plain RTSP only). Real-hardware
      verification (a real ONVIF NVT on a real LAN) remains the one open
      gap before this could be trusted in a real departmental deployment.

## Explicitly not doing (out of Model 2's scope this hackathon)

- **FastReID/OSNet deep Re-ID embedding.** Per `RESEARCH.md`: the real
  blocker isn't implementation effort, it's validation data — the
  sandbox doesn't produce enough cross-camera repeat sightings to
  meaningfully compare embeddings. Swapping algorithms without the
  ability to validate the swap would be worse than keeping the current,
  explainable, real-if-simple signal. Revisit only if a much larger/
  longer-running camera set becomes available.
- **Kafka/Elasticsearch.** Per `STRATEGY.md`'s scope discipline — pilot
  scale doesn't need them; `SCALABILITY.md` already documents them as the
  district/state-tier step.
- **A fake/simulated second system just to prove "≥2 systems."** Would be
  theater, not a real capability — this is why System B (see "Done"
  above) is a genuinely independent, real, live public government API
  (Caltrans D3), not a relabeled copy of the same sandbox data.
