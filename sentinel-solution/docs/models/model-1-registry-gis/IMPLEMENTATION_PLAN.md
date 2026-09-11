# Model 1 — Implementation Plan

Concrete remaining work only — this model is already built; nothing here
is a rebuild. Split into two tiers per the user's direction (2026-09-10):
**required-for-module** work (closes an explicit gap against the official
spec, tracked in `REQUIREMENTS.md`) comes first; **additional features**
(research-derived extras, beyond what the spec literally asks for) come
after, and only once the required tier is done or time-boxed. Effort
estimates are rough, single-developer, assuming familiarity with the
codebase (i.e. this session's pace, not a cold start).

**Status update 2026-09-11: Part 1 is fully closed.** All four R1–R3
items below shipped in `3306db6` the same day this plan was drafted —
ageing tracking, coverage-radius map layer, backend search/filter query
params, and the camera-onboarding audit trail. Backend suite was 53/53
after that commit; verified against `REQUIREMENTS_COVERAGE.md` and
`REQUIREMENTS.md` in this module folder. R4 (department data quality)
remains genuinely open — it's manual data entry, not code, and still
blocked on either organizer-provided ground truth or per-camera manual
assignment. Part 2 ("additional features") is untouched — none of those
schema extras have been built.

## Already closed this pass (2026-09-10)

- [x] Sample onboarded camera-metadata dataset →
      `samples/cameras_export_2026-09-10.csv`
- [x] Registry API documentation → `REGISTRY_API.md`
- [x] Sample gap-analysis report →
      `samples/gap_analysis_report_2026-09-10.{json,md}`

---

## Part 1 — Required for the module (closed 2026-09-10, `3306db6`)

Each item below mapped directly to one of the four 🟡 partial rows in
`REQUIREMENTS.md` — none were optional polish, they were the literal spec
text. All shipped same-day.

### R1 — "Interactive GIS map with department/type/status/coverage layers"

- [x] **GIS map coverage-radius layer.** `MapView.jsx` now renders a
      coverage-radius `Circle` per camera (`CameraRegistry.
      coverage_radius_m`) plus a dashed marker outline for ageing
      cameras, alongside the existing live/health color layer — closes
      the literal "layers" plural in the spec.

### R2 — "Gap-analysis reports for uncovered zones and ageing infra"

- [x] **Ageing-infrastructure field.** `CameraRegistry.install_date`
      (nullable datetime, additive migration) is live; `/cameras/
      gap-analysis` (JSON + PDF) reports cameras past
      `SENTINEL_CAMERA_AGEING_THRESHOLD_YEARS` (default 5) and
      `missing_install_date` separately. No fake dates were populated for
      the 30 sandbox cameras — honestly null where unknown, per the
      original recommendation.
- [ ] **True geospatial "uncovered zone" gap analysis (wedge/coverage-area
      union) — still open, not part of `3306db6`.** `coverage_radius_m`
      shipped as a flat radius per camera (good enough to close the R1
      map-layer and R2 ageing-report literal spec text), but the more
      ambitious per-camera `fov_deg`/`range_m` wedge-polygon + union-vs-
      patrol-boundary computation described here on 2026-09-10 was **not**
      built — this remains a genuine Part 2-style stretch item, not
      required for the module. Re-evaluate only if there's spare time
      after Model 2/3 work; not a submission blocker either way since
      `coverage_radius_m` already gives a real (if simpler) uncovered-zone
      signal via the map layer.

### R3 — "Role-based search, filtering, export, metadata audit trails"

- [x] **Backend search/filter query params on `GET /cameras`.**
      `department`, `camera_type`, `is_healthy`, `live`, `q` query params
      now filter server-side, applied before the existing department-
      scope filter — additive, no existing caller broke (no params =
      prior behavior).
- [x] **Camera-onboarding audit trail.** New `CameraAuditLog` table +
      admin-only `GET /cameras/{id}/audit-log`, kept separate from the
      purpose-bound vehicle-search `AuditLog` rather than overloading it.
      A regression test caught a real ordering bug (same-transaction
      edits tying on `created_at`, making `ORDER BY created_at DESC`
      nondeterministic) — fixed with an `id DESC` tiebreak.

### R4 — data quality, not code (still open — blocks R3's "role-based search" from being fully meaningful)

- [ ] **Department assignment for the 23 unassigned cameras.** Not a
      code fix (see `RESEARCH.md`'s open question) — needs either manual
      per-camera assignment via `POST /cameras` (admin), or a real
      authoritative department/location mapping if one becomes available
      from the organizers. Effort: ~30 min of manual entry if the mapping
      is known; otherwise blocked on external information.

---

## Part 2 — Additional features (beyond the literal spec, research-derived)

Only start these once Part 1 is done or explicitly time-boxed — these
strengthen the submission (compliance/jury credibility, richer metadata)
but don't close a `REQUIREMENTS.md` gap on their own. All four schema
items are additive nullable columns — no behavior change for existing
rows, no fabricated data needed for the 30 real sandbox cameras. See
`RESEARCH.md`'s "External precedent: camera vendors, types, and
registration attributes" section for full sourcing.

- [ ] **`stqc_certified` (bool, nullable) on `CameraRegistry`.** STQC
      (India MeitY cybersecurity certification) is required for
      government CCTV procurement; Hikvision/Dahua/Axis/Bosch/Hanwha/
      Panasonic i-PRO currently have zero STQC-certified models
      (Chinese-origin-chipset PPO bar), while CP Plus/Prama/Sparsh/Matrix/
      Honeywell do. This is a real, police-jury-relevant compliance
      dimension our schema has no field for at all. Effort: ~30 min
      (column + migration entry) + honest manual/null population — do
      not guess certification status for sandbox cameras whose actual
      vendor hardware isn't verifiable.
- [ ] **`onvif_profile` (string, nullable, e.g. "S"/"T"/"M"/"unknown") on
      `CameraRegistry`.** ONVIF Profile M is the metadata/analytics
      conformance profile (vehicle, license-plate, face metadata) —
      recording each camera's actual profile would let the registry
      honestly reflect which cameras can even emit the metadata our ANPR
      pipeline consumes, instead of assuming uniform capability. Also
      gives real per-camera evidence for our own "ONVIF interoperability"
      claim (`docs/strategy/RESEARCH_EXISTING_SYSTEMS.md` §2). Effort:
      ~30 min (column + migration) + null unless actually queryable from
      the sandbox catalogue/ONVIF device query.
- [ ] **`resolution_mp` (float, nullable) on `CameraRegistry`.** Commonly
      tracked in real camera-spec registries (open CC0 dataset,
      6,500+ models). Cheap demo value: `gap-analysis` could flag
      sub-HD cameras as a coverage-quality gap, not just missing-GPS/
      -department. Effort: ~45 min (column + migration + one new
      gap-analysis check, optional).
- [ ] **`ip_rating` (string, nullable, e.g. "IP67") on `CameraRegistry`.**
      Outdoor/traffic-junction durability attribute, matches how Indian
      Safe City deployments describe their camera specs. Effort: ~30 min
      (column + migration only, no gap-analysis logic needed).
- [ ] **Docs-only: suggested `camera_type` reference vocabulary.** No
      schema change (the field is deliberately free-text — see
      `db/models.py` docstring). Add the 11-value taxonomy
      (bullet/dome/turret/PTZ/dual-lens/panoramic/covert/box/fisheye/
      floodlight/doorbell) plus thermal/ANPR-dedicated as suggested
      values in `OnboardCameraForm.jsx`'s UI (e.g. a datalist/autocomplete,
      not a hard enum) so onboarding doesn't silently drift between
      "ptz"/"PTZ"/"pan-tilt-zoom" for the same real value. Effort: ~30
      min, frontend only.

---

## Explicitly not doing (out of Model 1's scope this hackathon)

Anything requiring a new database engine migration (PostgreSQL/PostGIS)
this week — per `STRATEGY.md`'s scope discipline, SQLite is correct for
pilot scale. Note the "uncovered zone" item above no longer needs this
migration at all (a 2D wedge approximation replaces the earlier PostGIS
assumption) — this exclusion now only covers a true 3D/precise spatial
index, which genuinely isn't justified without a real multi-hundred
-camera dataset.
