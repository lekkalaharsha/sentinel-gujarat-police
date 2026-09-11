# Model 1 — Research Notes

Model 1 is already built, so "research" here is grounding-in-reality
(what exists, verified against code) rather than external precedent
research (that's Model 3/4's job, where nothing is built yet).

## Ground-truth method

Read directly, 2026-09-10: `db/models.py` (`CameraRegistry`),
`api/routes_cameras.py` (every endpoint), `api/routes_admin.py`,
`scripts/onboard_from_catalogue.py`, `frontend/src/components/MapView.jsx`,
`LiveMapView.jsx`, `OnboardCameraForm.jsx`, `GapAnalysisPanel.jsx`,
`docs/HLD.md`, `docs/MODULE_GAP_ANALYSIS.md`. No claim in
`REQUIREMENTS.md` is asserted without a corresponding file/line citation
found this way.

## Key finding: one prior doc overclaimed

`docs/MODULE_GAP_ANALYSIS.md` (written 2026-09-05) states the GIS map has
"department + real health-status layers." Direct code inspection found
this is **not accurate** — `MapView.jsx` implements exactly one visual
layer (color-by-live-status); department/camera-type data is available
in the underlying API payload but never rendered as a separate, togglable
layer. This module's `REQUIREMENTS.md` corrects that claim rather than
repeating it — an example of exactly the kind of drift `CLAUDE.md` warns
about (a claim in one doc getting stale relative to the actual code).

## Precedent check: does our approach match how real registries work?

This model doesn't need external precedent research to justify its
architecture (it's a fairly standard CMDB/asset-registry pattern), but
two design choices are worth noting against how the official spec's
suggested stack anticipates this being used at scale:

- **PostGIS was suggested for spatial queries** (coverage radius,
  polygon zones) that this pilot doesn't yet need — 30 cameras is small
  enough that a linear scan with lat/lon equality checks is adequate.
  At district/regional scale (per `SCALABILITY.md`), a real PostGIS
  migration (radius queries, spatial indexes) becomes necessary — this
  is flagged, not silently deferred forever.
- **The "upsert onboarding" pattern** (`_apply_onboard_fields()` — a
  second onboarding call for an already-known ID updates rather than
  errors) matches how real fleet/asset registries are typically operated
  in practice (onboarding data arrives incrementally and gets corrected
  over time, not fully-formed on day one) — this wasn't derived from a
  specific external system, just standard practice, worth stating
  explicitly since it's a deliberate design choice.

## Open question surfaced by this pass

23 of 30 real sandbox cameras have no department assigned (see
`samples/gap_analysis_report_2026-09-10.json`). The onboarding script's
keyword-matching heuristic (matching department names appearing literally
in a camera's location string) only succeeds when the location happens to
mention a department — e.g. "Rajkot Bus Port CCTV" → GSRTC. For the other
23, no department name appears in the location text at all, so the
heuristic has nothing to match. This is not fixable by improving the
heuristic further — it needs either (a) manual assignment per camera, or
(b) a real department-to-location mapping table sourced from an
authoritative list (not available in the sandbox catalogue itself). Noted
in `IMPLEMENTATION_PLAN.md` as a data-quality task, not a code bug.

## External precedent: camera vendors, types, and registration attributes (added 2026-09-10)

Real web-research pass, distinct from `docs/strategy/RESEARCH_EXISTING_SYSTEMS.md`
(which covers VMS/analytics *software* vendors — Genetec, Milestone,
BriefCam, Frigate, Staqu, Videonetics — not camera *hardware* vendors or
registration-attribute schemas). Every claim below is sourced; anything
not found is stated as not found, not guessed.

### Camera hardware vendors — India-specific, with a genuinely
### submission-relevant compliance finding

STQC (Standardization Testing and Quality Certification, under India's
MeitY) certifies IP cameras for cybersecurity (default-password checks,
encrypted streams, secure boot, chipset-origin transparency).
**STQC certification is required for government/public-sector CCTV
procurement in India**, though not universally mandatory for private
buyers. As of a 2026 industry summary, ~196 STQC-certified models exist
across Prama (58), CP Plus (45), Sparsh (43), Matrix (36), Honeywell (9),
Vicon (3), Equus (2)
([FGTech STQC list](https://fgtechstore.com/blog/bis-stqc-certified-cctv-camera/)).
**Hikvision, Dahua, Axis, Hanwha, Bosch Security, and Panasonic i-PRO have
zero STQC-certified models** — barred from new Indian government-tender
sales because their hardware typically uses Chinese-origin chipsets,
which India's PPO (Public Procurement Order) rules for
government-preferential-purchase disqualify from certification. Hikvision
sells into the Indian market only via its Prama joint venture, under the
Prama brand/certification, not Hikvision's own.

This directly matters for Sentinel: our sandbox catalogue's real `vendor`
field values are unverified for STQC status, and this is a genuine,
citable, jury-relevant compliance dimension for a **police-department**
CCTV registry that our current schema has no field for at all.

### Camera type taxonomy — an existing open-source enum worth citing

A real, actively-maintained open dataset
([ch-bas/cctv-camera-database](https://github.com/ch-bas/cctv-camera-database),
6,500+ camera models across 134 brands, CC0) defines an 11-value
`camera_type` enum: `bullet, dome, turret, PTZ, dual-lens, panoramic,
covert, box, fisheye, floodlight, doorbell`. General-purpose taxonomy
sources ([getsafeandsound.com](https://getsafeandsound.com/blog/types-of-cctv-systems/),
[a2zsecuritycameras.com](https://www.a2zsecuritycameras.com/camera-types-bullet-dome-turret-fisheye-ptz-guide/))
confirm the same core set plus the two specialty types most relevant to
traffic/ANPR deployments: **thermal** (heat-signature detection, no
visible light needed) and **ANPR/LPR-dedicated** (purpose-built plate-read
optics, distinct from a general fixed camera). Our own Indian Safe City
research (below) confirms ANPR, Fixed, RLVD (red-light-violation
detection), and PTZ as the four types actually deployed at Indian traffic
junctions.

This validates `CameraRegistry.camera_type`'s existing design choice
(free-text, not an enum — see the docstring in `db/models.py`) rather than
changing it: the field already accepts any of these values, and rejecting
an unrecognized one would be worse than storing it as-is. No schema
change justified here — just a documented reference vocabulary for the
onboarding UI to suggest.

### Registration-attribute schemas from real registries — the useful finding

Three independent, citable sources converge on a similar attribute set
beyond what `CameraRegistry` currently stores:

1. **UK Surveillance Camera Code of Practice** (statutory, under the
   Protection of Freedoms Act 2012) explicitly requires that
   "meta data (e.g. time, date and location) [be] recorded reliably" for
   every surveillance camera in scope
   ([gov.uk PDF](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/1055736/SurveillanceCameraCodePractice.pdf)).
   No further granular field list was found in the Code itself or the
   Commissioner's public guidance — this is a real limit of what's
   publicly documented, not a gap in this research pass.
2. **ONVIF Profile M** (the metadata/analytics conformance profile) — its
   published spec ([onvif.org, v1.1](https://www.onvif.org/wp-content/uploads/2024/04/onvif-profile-m-specification-v1-1.pdf))
   defines structured metadata fields for **geolocation, vehicle, license
   plate, human face, and human body** detection events, plus object
   counting and rule configuration. Directly relevant: Sentinel already
   claims ONVIF as its device-abstraction standard
   (`docs/strategy/RESEARCH_EXISTING_SYSTEMS.md` §2) — recording each
   camera's actual **ONVIF conformance profile** (S = streaming only, T =
   advanced streaming, M = metadata/analytics) at registration time would
   let the registry honestly reflect which cameras can even emit the
   vehicle/plate metadata our ANPR pipeline consumes, rather than
   assuming uniform capability across all 30 sandbox cameras.
3. **The open camera-spec dataset above** (`ch-bas/cctv-camera-database`)
   lists real, commonly-tracked hardware attributes beyond ours:
   `resolution` (megapixels), `ip_rating` (ingress protection, e.g. IP67
   for outdoor durability), `night_vision.range_m`/`min_lux_color`,
   `protocols` (ONVIF/RTSP support flags), and `power.method`.

Indian Safe City DPRs (Delhi, Noida, Bengaluru — city-level Detailed
Project Reports) confirm **HD/night-vision resolution and camera-type
mix (ANPR/Fixed/RLVD/PTZ)** as the specified attributes at
procurement/installation time, consistent with the above
([Deccan Herald](https://www.deccanherald.com/india/karnataka/bengaluru/3400-cctv-cameras-to-be-installed-under-bengaluru-safe-city-project-1204531.html),
[Delhi DDC](https://ddc.delhi.gov.in/our-work/6/delhi-city-surveillance-cctv-project),
[99acres/Noida](https://www.99acres.com/articles/noida-safe-city-project.html)).
No public DPR was found with a field-by-field camera-metadata schema
(DPRs describe deployment counts/locations, not a database schema) — that
level of detail isn't published, so this is inferred from deployment
descriptions, not a literal schema citation.

### Military/defense CCTV registry precedent — not found, stated honestly

Searched specifically for military-base perimeter-camera *registry/asset
schema* precedent. Found only generic military CMMS/asset-tracking
platforms (RFID/RTLS-based, e.g. BarCloud, Ubisense) covering *all*
military hardware categories in general terms — tamper-proof audit trails,
condition-based maintenance, FSRM budget justification — with **no
camera-specific attribute schema publicly documented**. This is a
genuine dead end for this pass, not a claim that none exists (defense
asset-management schemas are plausibly non-public for security reasons)
— reported honestly rather than extrapolated from the generic-asset
material found.

### Research papers — limited direct hits

No paper was found specifically proposing a CCTV-registry/camera-asset
metadata *schema*. Adjacent IEEE material exists on smart-city
surveillance architecture generally (e.g. an IEEE Smart Cities newsletter
piece on an open-source situational-awareness pipeline that does list
per-camera metadata — location, RTSP URI, facing direction, description —
as inputs to its ML pipeline
([IEEE Smart Cities, Jan 2023](https://smartcities.ieee.org/newsletter/january-2023/data-analytics-using-open-source-tools-for-a-smart-city-situational-awareness-solution-at-the-edge)),
which is the closest independent confirmation that "location + direction
+ description" (fields we already have via `location_name`/
`expected_direction_deg`) is a reasonable minimal set — but no dedicated
academic schema-design paper was found. Reported as a real gap in the
literature, not filled with a fabricated citation.

### Recommended new `CameraRegistry` attributes, ranked by value ÷ effort

1. **STQC/BIS certification status** (`stqc_certified: bool | None`, or a
   richer `compliance_status` string). Highest value: a real,
   police-jury-relevant compliance dimension unique to Indian government
   procurement, near-zero engineering cost (one nullable column, populated
   manually or left null/unknown — same honesty pattern as `is_healthy`).
   Source: STQC/PPO finding above.
2. **ONVIF conformance profile** (`onvif_profile: str | None`, e.g.
   "S"/"T"/"M"/"unknown"). Directly supports our own ONVIF-interoperability
   claim with real per-camera evidence instead of an assumed uniform
   capability. Source: ONVIF Profile M spec above.
3. **Resolution** (`resolution_mp: float | None`). Cheap, commonly tracked,
   demo-relevant (a gap-analysis report could flag sub-HD cameras).
   Source: open camera-spec dataset.
4. **IP rating** (`ip_rating: str | None`, e.g. "IP67"). Relevant to
   outdoor/traffic-junction durability, matches Indian Safe City camera
   descriptions. Source: open camera-spec dataset + Safe City DPR pattern.
5. **Suggested `camera_type` reference vocabulary** (docs/UI-only, no
   schema change) — the 11-value enum above, to make the existing
   free-text field's onboarding UI suggest consistent values rather than
   accept arbitrary strings silently drifting (e.g. "ptz" vs "PTZ" vs
   "pan-tilt-zoom" today). Source: open camera-spec dataset.

Items 1–4 are new nullable columns — additive migrations, no behavior
change for existing rows (matches the `installed_at` pattern already
planned in `IMPLEMENTATION_PLAN.md`). None require populating fabricated
data for the 30 real sandbox cameras; nulls are honest where the sandbox
catalogue doesn't expose the underlying fact.

### Sources

- [Surveillance Camera Code of Practice (gov.uk PDF)](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/1055736/SurveillanceCameraCodePractice.pdf)
- [ONVIF Profile M Specification v1.1](https://www.onvif.org/wp-content/uploads/2024/04/onvif-profile-m-specification-v1-1.pdf)
- [ch-bas/cctv-camera-database (GitHub, CC0 camera-spec dataset)](https://github.com/ch-bas/cctv-camera-database)
- [STQC-certified CCTV camera list, 2026 (FGTech)](https://fgtechstore.com/blog/bis-stqc-certified-cctv-camera/)
- [Bengaluru Safe City project — 3,400 cameras (Deccan Herald)](https://www.deccanherald.com/india/karnataka/bengaluru/3400-cctv-cameras-to-be-installed-under-bengaluru-safe-city-project-1204531.html)
- [Delhi City Surveillance CCTV Project (DDC Delhi)](https://ddc.delhi.gov.in/our-work/6/delhi-city-surveillance-cctv-project)
- [Noida Safe City Project — 2,100 cameras (99acres)](https://www.99acres.com/articles/noida-safe-city-project.html)
- [IEEE Smart Cities — open-source situational-awareness pipeline, camera metadata fields (Jan 2023)](https://smartcities.ieee.org/newsletter/january-2023/data-analytics-using-open-source-tools-for-a-smart-city-situational-awareness-solution-at-the-edge)
- CCTV type taxonomy: [getsafeandsound.com](https://getsafeandsound.com/blog/types-of-cctv-systems/), [a2zsecuritycameras.com](https://www.a2zsecuritycameras.com/camera-types-bullet-dome-turret-fisheye-ptz-guide/)
- Military asset management (general, not camera-schema-specific):
  [BarCloud](https://barcloud.com/industries/military/), [Ubisense](https://ubisense.com/asset-tracking-weapons/)
