# Model 2 — Implementation Plan

Concrete remaining work only — this model is already built and verified
against real sandbox footage; nothing here is a rebuild. Unlike Model 1,
Model 2 has **no required-tier gaps against the literal spec text** — the
one 🟡 in `REQUIREMENTS.md` ("≥2 different systems") is a sandbox-
availability limit, not missing code. Everything below is Part
2-equivalent: research-derived hardening, useful if time allows, not a
submission blocker.

## Not required, no action needed

- **"Unified viewer connecting ≥2 different systems."** **Qualified
  2026-09-11** (an independent project review found this claim overstated
  as originally written): "zero code change" is only true for a second
  source that already exposes a `cameras.json`-shaped catalogue with
  self-contained stream URLs, matching `CameraInfo.from_api`'s expected
  shape (`catalogue.py`). A genuinely different real VMS/vendor system —
  the case the hackathon spec actually means by "different systems" —
  needs a new adapter, exactly like Model 3's `VMSAdapter` pattern. This
  was proven directly: adding real ONVIF discovery as a second
  ingestion path (`streaming/onvif_discovery.py`, 2026-09-11) required a
  new ~250-line module, new config surface, and 14 new tests — not zero
  code. The corrected claim: the *registry and viewer layer* is already
  source-agnostic (Model 1's registry + Model 2's `StreamManager` don't
  hardcode "the sandbox"), so onboarding a second source is a new-adapter-
  sized change, not a rewrite — but it is not a zero-code-change event.
  Don't simulate a fake second system to check this box — that would be
  dishonest demoing, not a fix.
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
- **A new department VMS integration just to prove "≥2 systems."** Would
  be theater, not a real capability — see "Not required, no action
  needed" above.
