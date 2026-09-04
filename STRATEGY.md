# Sentinel — Strategy Decision (synthesized from ChatGPT + DeepSeek research, 2026-09-03)

## The pitch correction (highest-leverage change, zero code cost)

Gujarat Police already operates **VISWAS/NETRAM/TRINETRA**: 7,000+ cameras, 34 district
NETRAM command centres feeding a state-level TRINETRA ICCC, integrated with VAHAN/SARTHI,
with a Phase-II expansion already adding ~10,500 more cameras. A jury with real Gujarat
Police knowledge will ask "what did you invent?" if we pitch a from-scratch unified CCTV
platform.

**Do not pitch:** "We built a centralized CCTV command platform for Gujarat."

**Pitch instead:** "Sentinel is an open, vendor-neutral **interoperability and intelligence
layer** that sits above existing departmental CCTV/VMS infrastructure (including systems
like TRINETRA/NETRAM) — registering cameras, normalizing heterogeneous feeds into one
canonical event model, correlating vehicle observations across cameras, and connecting
those events to authorized government databases — without requiring departments to
replace what they already run."

**The same correction applies to the AI layer, not just the VMS layer** (added after
competitor research — see `RESEARCH_EXISTING_SYSTEMS.md` §7): detection, ANPR, and
cross-camera vehicle tracking are already shipped commercially in India (Staqu JARVIS,
Videonetics, Vehant, Innefu). Do **not** pitch those as the invention. Sentinel's
genuine, defensible contribution is the **open, explainable vehicle-identity-resolution
layer** — a persistent vehicle entity built from uncertain observations (plate-OCR
confidence + appearance + temporal feasibility + recency) with an explainable link trail,
degrading gracefully to attribute tracking when the plate can't be read. This is already
built (`identity.py` + `link_method`/`link_score`); the correction is about *framing* it
honestly, not building anything new. Frame it as "identity resolution," not "Re-ID" —
Re-ID is one input signal, not the whole mechanism.

## Model choice: explicit hybrid (decided 2026-09-03)

Positioning is a **Model 1 + Model 2 hybrid**, with the Model 3/4 (federation → central
AI platform) path documented as the production roadmap but NOT claimed as built. Rationale:
"combine elements from two or more models" is the rules' own definition of a hybrid (§7),
and "innovative hybrid/customized architecture with operational value" is an explicit
**bonus** criterion (§10) — so we claim hybrid credit for what's genuinely built and show
the federation/central-VMS evolution as roadmap, without overstating. Building a real
per-vendor VMS federation bus (Model 3) stays on the OUT list — not achievable in the
window, and a half-built federation layer would be worse than an honest documented path.
The HLD (§1) states this framing directly.

## Architecture decision

Keep the current FastAPI + camera-registry + resilient-RTSP scaffold as the **pilot/edge
tier**. Frame it explicitly in the HLD as one instance of a repeatable pattern, not the
final centralized architecture. Production target (diagram for HLD, not fully built this
week):

```
26 Departments (incl. existing VMS/TRINETRA/NETRAM)
        │  ONVIF / RTSP / API
        ▼
Sentinel Connector (protocol + stream normalization)
        │
        ▼
Regional media fabric (future: MediaMTX/go2rtc — cite as planned, not built this week)
        │  selective video, not everything
        ▼
AI fabric: Detector → ByteTrack (within-camera) → ANPR → Re-ID (cross-camera confirmation)
        │
        ▼
Event plane: canonical event schema, PostgreSQL/PostGIS, vehicle identity, watchlist
        │
        ├──► Watchlist engine → alerts
        └──► Authorized government DB queries (VAHAN etc.) — query, don't copy
        ▼
Governance plane: RBAC, purpose-bound queries, audit log, retention policy
```

Key principle to state explicitly in the HLD: **centralize metadata/events/identity/GIS/
governance — not every raw video frame.** (Bandwidth math for the record: 80,000 cameras
× ~2 Mbps ≈ 160 Gbps sustained, ~1.7 PB/day — full central raw-video ingestion is not a
credible target and we say so, rather than pretending otherwise.)

## What's IN for the 4-day build

- Camera registry + GIS (already built, Model 1)
- Resilient RTSP consumer, PTS-driven timing (already built, validated against real cam01)
- Vehicle detector → plate detector → **PaddleOCR** (swap from EasyOCR stub — more current,
  Apache 2.0, actively maintained) → temporal plate-read fusion (don't trust a single OCR read)
- **ByteTrack** for within-camera multi-object tracking (well-benchmarked, cheap to integrate)
- Plate-first identity, with vehicle Re-ID (FastReID/OSNet, pretrained) as a *secondary*
  confirmation signal only if time allows — not a required path
- Watchlist + alert engine (already built)
- **Purpose-bound queries + audit log** — every plate lookup carries user/purpose/case_id,
  logged. Cheap, and both research passes independently flagged this as jury-relevant.
- "Why was this vehicle linked?" explainability panel: show plate confidence + (if present)
  re-ID similarity + temporal consistency → fused association score. Strong, cheap demo beat.
- Movement-history timeline + GIS route rendering (already have the API; needs frontend)
- **Geo-temporal route reconstruction (added 2026-09-03 — the differentiator
  layer, matches the "advanced cross-camera correlation" bonus criterion).**
  Between two CONFIRMED sightings, the movement history now interleaves
  honestly-labelled **INFERRED** camera-less segments: straight-line
  (haversine) distance between camera GPS + time-gap → a plausibility check
  (`analytics/geo.py`, surfaced in `/vehicle/{plate}/history` and the
  timeline UI). Event typing is **OBSERVED vs INFERRED** — inferred movement
  is never presented as observed fact (police-credibility point). Scope
  discipline: this is straight-line/lower-bound only; **full road-network
  (OSM) routing and forward "PREDICTED next-camera" pruning stay on the
  roadmap** (OSM coverage of Gujarat's minor roads is incomplete, and
  candidate-pruning buys nothing observable at 50-camera demo scale — its
  value is the 80k scalability narrative). ETA-based candidate pruning, if
  built later, must be a soft ranking hint, never a hard filter, and must
  never override a confirmed plate read.

## What's OUT — explicitly deferred, say so in the HLD, don't apologize for it

- Face recognition (legal/DPDP risk, NIST-documented demographic bias, not needed for the
  required plate-tracking test case)
- Fingerprint/biometric database integration
- Generic/unscoped anomaly detection (replace with named, measurable events if time allows:
  wrong-way vehicle, stopped-in-restricted-zone — otherwise skip entirely)
- Full 80,000-camera physical ingestion — instead demonstrate the **control plane** scales
  independently: real 30 cameras + a larger simulated registry showing health/status at scale
- Building a new VMS, or full VMS federation middleware
- Actually deploying MediaMTX/go2rtc/Kafka this week — cite as the documented production
  path in the HLD; our direct-RTSP pilot is explicitly labeled as the demonstrable subset

## DPDP note (for the HLD's legal/compliance section)

Section 17 of the DPDP Act 2023 exempts processing for prevention/detection/investigation/
prosecution of offences — but don't claim blanket exemption to the jury. Design as if the
Act's substantive obligations (Sections 3–17, staged commencement ~18 months from
13 Nov 2025) apply anyway: purpose limitation, data minimization, retention limits, audit
logs. This is why purpose-bound queries and audit logging are worth the build time.
