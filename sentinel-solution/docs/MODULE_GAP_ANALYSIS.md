# Module Gap Analysis — Sentinel vs. Hackathon Reference Models

Checked against the actual codebase (routes, DB models, frontend components), not assumed. Generated 2026-09-05. Update this file as modules are checked and gaps closed.

**Hybrid/innovation architecture note:** the rules explicitly permit combining "suitable elements from two or more models" rather than picking exactly one — this isn't a fallback, it's the sanctioned path. Sentinel's Model 1+2 hybrid (mandatory registry/GIS base + direct unified viewing, with Model 3/4 as a documented, not-implemented, roadmap) is squarely within that allowance, not a compromise against it. Worth stating that framing explicitly and confidently in the Solution Presentation, rather than apologizing for not building all four models.

---

## Model 1 — Central CCTV Registry & GIS

### Missing
- **Coverage-radius/zone map layer** — map shows point markers only, no coverage-area overlay.
- **Ageing-infrastructure tracking** — no installation-date/equipment-age field; gap-analysis can't report "ageing" cameras, only unhealthy/unregistered ones.
- **Camera-onboarding audit trail** — `AuditLog` exists and is real, but only logs vehicle-search purpose/case_id lookups, not who onboarded/edited which camera and when.
- **PostgreSQL + PostGIS** — running on SQLite for the pilot. Fine for hackathon scale; needs an explicit line in the HLD calling this out as the production target, not a silent gap.

### Already built (confirmed in code)
- Bulk (`POST /cameras/bulk`), manual, and API onboarding (`POST /cameras`)
- GIS map with department + real health-status layers (Leaflet)
- Camera health/maintenance monitoring, backed by real RTSP worker connection state (not simulated)
- Gap-analysis report: live-but-unregistered, registered-but-offline, missing department, missing GIS coords, unhealthy, by-department breakdown (`GET /cameras/gap-analysis`)
- Role-based access control, real 401/403 enforcement
- Sample dataset: 30 onboarded cameras
- API docs: implicit via FastAPI's auto-generated OpenAPI schema at `/docs`
- **`camera_type` field (PTZ/dome/fixed/bullet) — done 2026-09-05.** `CameraRegistry.camera_type`, onboarding form + API, CSV export, JSON view.
- **Camera export — done 2026-09-05.** `GET /cameras/export.csv`, department-scoped and admin-credential-safe (never emits rtsp_url/whep_url), verified via real HTTP calls.
- **Department-scoped RBAC — done 2026-09-05.** `api/auth.py`'s `department_scope()`: a non-admin key tied to a department only sees that department's registered cameras (list/get/export/gap-analysis all scoped consistently); admin and department-less keys stay unrestricted. Deliberately does NOT scope vehicle search/history — see the code's docstring for why (cross-department correlation is the core differentiator, not a gap to restrict). Verified with 5 new pytest tests (`tests/test_rbac_department_scope.py`) plus real HTTP calls across two department-scoped keys.
- **Backend search/filter on `/cameras`** — still client-side only; not addressed this pass (lower priority than the three items above).

---

## Model 2 — Unified Viewing Platform (Direct Integration)

### Missing
- **ONVIF integration** — HLD documents ONVIF as the target device-abstraction standard but explicitly notes it isn't implemented; the sandbox only exposes plain RTSP, so the pilot connects directly to that instead.
- **Vendor SDK integration** — not implemented (no vendor-specific systems available to integrate against in the sandbox).
- **WebRTC/WHEP low-latency preview** — HLD documents this as not implemented; only HLS relay exists.
- **Event tagging** — `VehicleEvent` rows are camera-indexed, but there's no user-facing feature to attach custom tags/labels to an event.
- **Kafka/message-bus event pipeline** — HLD documents this as a production-scale item (event bus between per-department connectors and AI pipeline), not built for the pilot.
- **Elasticsearch** — not used; search runs directly against SQLite/SQLAlchemy queries. Fine at pilot scale, needs the same "documented production target" treatment as PostGIS.
- **"At least two different departmental systems" deliverable** — we integrate against **one** system (the hackathon sandbox), not two distinct real departmental VMS platforms. Worth flagging explicitly in the submission rather than implying multi-vendor integration was demonstrated.

### Already built (confirmed in code)
- RTSP feed aggregation (real, PTS-driven, reconnect-with-backoff — not a stub)
- HLS relay for browser playback, proxied through an authenticated backend endpoint (`routes_stream.py`) so the sandbox password never reaches the browser
- ANPR-based metadata generation: real YOLOv8 detection + PaddleOCR, not stubs
- Searchable vehicle-movement records (`/vehicle/{plate}/history`, cross-camera timeline)
- Alerts for watchlisted vehicles, governed lifecycle (new → acknowledged → resolved/dismissed)
- Camera-wise indexing: every `VehicleEvent` carries `camera_id`, queryable per camera
- **Configurable video wall / multi-camera grid — done 2026-09-05.** `CameraGridView.jsx`: up to 9 simultaneous live HLS tiles, each its own independent `LiveView` instance (own hls.js session, own error isolation — one camera's stream failure doesn't affect the others). Verified visually via Playwright against the real live sandbox: tiles render correctly in a responsive grid with correct labels/selection state. One pre-existing, unrelated finding surfaced during this verification: the HLS proxy (`routes_stream.py`) returned 502 for several real cameras' segments during this test session — reproduced with a plain `curl` outside the new component too, so it's a pre-existing sandbox/proxy reliability issue, not something the grid feature introduced. Worth a closer look before the government-feed demo video.
- **Named anomaly alerts (wrong-way / stopped-in-restricted-zone) — done 2026-09-05.** `analytics/anomaly.py`: opt-in per camera (`CameraRegistry.is_restricted_zone`/`expected_direction_deg`), built on the motion data (`speed_px_per_s`/`direction_deg`/`dwell_time_s`) that already existed. Same governed alert lifecycle as watchlist alerts, badged separately in the UI (`alert_type`). Verified with a dedicated runtime test covering both trigger conditions, the no-config-no-alert case, near-stationary-noise suppression, and dedup against an already-open alert.

---

---

## Model 3 — Middleware / Federation Layer

**Different situation from Models 1/2: this is a deliberately, explicitly out-of-scope architecture, not an oversight.** `HLD.md` §1 states plainly: *"Building a real per-vendor VMS federation bus (Model 3) is deliberately out of scope for the build window... claiming it as built would be exactly the kind of overstatement this submission avoids."* Our chosen architecture (Model 1+2 hybrid, direct connection) is presented as what a Model 3/4 evolution would *extend*, not as Model 3 itself.

### Missing (all of it, by design)
- Adapter/plugin architecture for multiple VMS vendors — we connect to one system (the sandbox) directly, not through per-vendor adapters.
- Metadata exchange bus (Kafka/RabbitMQ) — not implemented; documented in `HLD.md` as a production-scale item.
- Cross-system event-correlation engine — our identity resolution correlates across *cameras*, not across *separate VMS platforms/systems*.
- Unified workflow/alert dashboard federating multiple source systems — our dashboard is unified, but over one source, not several federated ones.
- Extensible connector framework for onboarding future vendors — no plugin/connector abstraction exists; the RTSP client is written directly against the sandbox's specific integration guide.
- API Gateway (Kong/NGINX), Redis — not used.

### Adjacent capability that exists
- The RTSP ingestion layer (`streaming/rtsp_client.py`, `StreamManager`) is already a clean seam a future adapter-per-vendor layer could sit behind — it's not vendor-agnostic today, but it's not tangled into the rest of the pipeline either.

---

## Model 4 — Fully Centralised Statewide VMS

**Same situation as Model 3: explicitly deferred, not attempted.** `HLD.md` §1 argues against building this from scratch — Gujarat already runs VISWAS/NETRAM/TRINETRA at real scale (7,000+ cameras), so a from-scratch centralized VMS invites "what did you invent that doesn't already exist?" Our submission targets Model 1+2 as the honestly-achievable base.

### Missing
- Tiered hot/warm/cold storage — we have a single-tier retention/purge policy (`db/retention.py`, DPDP-driven), not literal storage-class tiering.
- Face recognition — explicitly out of scope project-wide (legal/DPDP risk, documented bias — `STRATEGY.md` OUT list), not just missing from this model.
- Crowd counting — not built at all.
~~Named anomaly detection (wrong-way vehicle, stopped-in-restricted-zone)~~ — **done 2026-09-05**, see Model 2's "Already built" list above.
- Integration with VAHAN, SARTHI, eGujCop/CCTNS, AFIS, NAFIS — none built or stubbed. `HLD.md` names these as the real enforcement databases the platform would eventually query (not copy data from), but no code exists yet, not even a stub interface.
- Redundancy, disaster recovery, network segmentation — single-instance pilot; none of these exist, by design at this scale.
- Kubernetes orchestration, distributed object storage (S3/Ceph), TimescaleDB — not used; SQLite + local disk for the pilot.
- Statewide-scale load testing / 80,000-camera scalability report — not run (would need to be a documented projection/estimate for the Scalability Strategy deliverable, not an actual load test).

### Adjacent capability that exists
- Centralized ingestion pattern (`StreamManager` managing multiple camera workers from one process) is the same *shape* Model 4 needs, just not deployed at statewide scale — this is explicitly the "control plane scales, physical ingestion doesn't (yet)" narrative already in `STRATEGY.md`.
- Cross-camera vehicle tracking/route reconstruction already works at pilot scale (5-30 cameras) — the same identity-resolution mechanism Model 4 would need statewide, not a different one.
- RBAC exists and is real, though not yet paired with the encryption/network-segmentation layer a statewide deployment would need.

---

---

## Key Challenges (problem-statement-wide, not model-specific)

| Challenge | How Sentinel addresses it | Gap |
|---|---|---|
| **01 Heterogeneous infrastructure** (vendors, VMS, AMC periods, storage, camera types/formats/protocols) | RTSP/HLS direct-connection pattern (Model 2); ONVIF named in the HLD as the vendor-neutral target standard | Only tested against **one** real system (the hackathon sandbox) — multi-vendor handling is a stated design intent, not proven against a second real VMS/vendor |
| **02 Geographical dispersion** (~1,000km across the State) | GIS registry is lat/lon-based with no distance assumptions baked in; HLS/CDN-style delivery is distance-agnostic in design | Real bandwidth/latency behavior over actual long-haul links to remote districts (e.g. border areas) is untested — this needs to be a stated assumption in the Scalability Strategy doc, not a measured result |
| **03 Unified analytics** across onboarded cameras | Solid — one pipeline (YOLOv8 + PaddleOCR + identity resolution) processes every camera identically, with real cross-camera correlation | None found |
| **04 Scalability** (onboard cameras/departments without major redesign) | Onboarding API (bulk/manual/API) and per-camera worker pattern already support adding cameras without code changes | Real horizontal scaling (sharding workers across machines, load balancing) isn't implemented — single-process pilot today. The 80k-camera story has to be *argued* in the Scalability Strategy doc, not demonstrated in running code |

**Discussion points (need a decision, not just documentation):**
1. **Multi-vendor claim risk — resolved 2026-09-10.** We can honestly say the *architecture* is vendor-neutral (RTSP/ONVIF-based, no vendor-specific code baked into the core pipeline), but we cannot claim it's been *proven* against a second real vendor system, because the sandbox only exposes one. `HLD.md`'s ONVIF wording was already careful ("targets ONVIF" as a design standard); the actual risk was `docs/submission/EMAIL_DRAFT.md`, which named VISWAS/NETRAM/TRINETRA alongside "vendor-neutral" with no "designed for, not proven against" caveat — reworded to make explicit that this submission demonstrates the architecture against the hackathon sandbox, not a live VISWAS/NETRAM/TRINETRA connection.
2. **Private/commercial CCTV support — resolved 2026-09-10.** The background text explicitly asks for "viewing capabilities for public-facing CCTV cameras installed by societies, malls, commercial establishments... wherever feasible and permitted." Added a paragraph to `HLD.md`'s onboarding section: private/commercial cameras use the same onboarding flow as departmental ones, tagged by owning entity, contingent on that entity granting access — explicitly labeled design-only, not built or demonstrated (no such feeds exist in the sandbox to test against).
3. **External DB integration honesty — already closed.** VAHAN/SARTHI/eGujCop/AFIS/NAFIS are named as required integrations for "automated real-time alerts." We have zero code or stub for any of them — our watchlist is a local table we seed ourselves, not a live query against a real government database. `HLD.md` (near line 439-447) already states the "query, don't copy" principle explicitly for VAHAN/SARTHI/eGujCop/CCTNS, with the watchlist described as local seed data — no further doc change needed.

---

## Scalability Strategy deliverable — checked against HACKATHON_DETAILS.md §9.5's exact checklist

`SCALABILITY.md` exists and is substantial. Checked item-by-item:

| Required item | Status |
|---|---|
| Central/regional/edge compute | ✅ §2, with a real tier table |
| GPU/accelerator requirements | ✅ §2 (GPU accelerator estimate subsection) |
| Network bandwidth + low-bandwidth strategies | ✅ §3, names Valsad/Dahod/Dwarka explicitly |
| Hot/warm/cold storage tiers | ✅ §4 |
| Load balancing, horizontal scaling | ✅ §5 |
| Monitoring, health checks | ✅ §5 (ties to the real `CameraRegistry.is_healthy`/gap-analysis mechanism) |
| High availability, disaster recovery | ✅ §5 (Postgres primary/replica, automated failover) |
| **Backup** (as distinct from DR failover) | ✅ **Fixed 2026-09-05** — added to `SCALABILITY.md` §5 (Postgres base backups + WAL archiving, separate-region storage) |
| **Cybersecurity controls: encryption at rest/in transit** | ✅ **Fixed 2026-09-05** — added (TLS every hop, disk encryption, ties to existing hashed-API-key + proxied-credential implementation) |
| **Cybersecurity controls: network segmentation** | ✅ **Fixed 2026-09-05** — added (department-segmented edge, gateway-only central access) |
| Estimated implementation and operational costs | ✅ §7, explicitly labeled as planning-magnitude estimates, not a procurement quote |

All 11 required items are now covered in `SCALABILITY.md`.

---

## Suggested next actions

~~1. Quick wins: `camera_type` field + CSV export~~ — **done 2026-09-05.**
~~2. Bigger lift: live multi-camera grid~~ — **done 2026-09-05.**
3. Documentation-only fixes: add the "PostgreSQL/PostGIS and Kafka/Elasticsearch are the documented production target, SQLite/direct-query is the pilot substitute" framing explicitly to the HLD if not already prominent, and be explicit in the submission that the sandbox is one integration point, not two. Still open.
~~4. HLS-proxy 502 reliability issue~~ — **root-caused and fixed 2026-09-05**: CDN User-Agent gate, see `sentinel-solution/README.md`'s "Known issues" for detail. This was blocking live view generally (not just the new grid), so this fix directly de-risks the government-feed demo video.
