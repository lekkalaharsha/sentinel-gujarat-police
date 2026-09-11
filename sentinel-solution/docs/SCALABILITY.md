# Sentinel — Scalability Strategy (Plan for Scale)

**Submission deliverable per HACKATHON_DETAILS.md §9.5.** Covers
central/regional/edge compute, GPU/accelerator sizing, network bandwidth
planning, storage tiers, load balancing/HA/DR, and a rough cost estimate
for scaling from this submission's ~30-camera pilot to the ~80,000-camera
statewide target. Numbers here are engineering estimates for planning
purposes, not vendor quotes — labeled as such throughout.

## 1. Why full central video ingestion is not the plan

80,000 cameras × ~2 Mbps average bitrate ≈ **160 Gbps sustained** ingress,
≈ **1.7 PB/day** of raw video if centralized. That is not a credible
target for any team at hackathon scale, and pretending otherwise in a
scalability document would be the least credible thing we could submit to
a technical jury. The architecture instead centralizes **structured
events**, not frames:

```
Per camera: ~1 vehicle event/sec peak (urban junction) × ~1 KB/event (plate,
timestamp, camera_id, embedding, confidence) ≈ 1 KB/s/camera

80,000 cameras × 1 KB/s ≈ 80 MB/s ≈ 640 Mbps sustained event-plane traffic
```

That's a **~250x reduction** versus raw video (160,000 Mbps ÷ 640 Mbps —
corrected 2026-09-11 from an earlier "three orders of magnitude"/~1000x
claim, which was arithmetically wrong; independently recomputed during a
project review), and it's still what makes a Kafka/PostgreSQL-based event
plane a realistic central tier even at full scale. Video itself stays
regional/local — see §3. Note the 640 Mbps side is itself an
underestimate for planning purposes: it excludes JSON/protocol overhead,
evidence-crop transmission, and replica-write traffic, so the real
achievable reduction in production is likely somewhat less than 250x, not
more.

## 2. Compute tiers

| Tier | Role | Sizing basis |
|---|---|---|
| **Edge** (per camera cluster / NVR site) | RTSP ingestion, frame sampling, YOLOv8 + PaddleOCR inference, within-camera tracking | 1 GPU (e.g. T4-class) comfortably handles ~15–25 concurrent camera streams at `ANALYTICS_FRAME_STRIDE=5` sampling with YOLOv8n + PaddleOCR (mobile-scale models chosen specifically for this — see STRATEGY.md) |
| **Regional** (per district/NETRAM-equivalent) | Cross-camera Re-ID within the region, regional event aggregation, regional media fabric (MediaMTX/go2rtc) for selective live relay | Scales with camera count per district; Gujarat's existing 34 NETRAM centres are a natural regional boundary to align with, not duplicate |
| **Central** (state-level, TRINETRA-equivalent) | Cross-region identity correlation, watchlist matching, RBAC/audit, GIS registry, public-facing dashboards | Horizontally scaled API + DB tier; this submission's FastAPI + SQLAlchemy code is the same code that runs here, pointed at PostgreSQL instead of SQLite |

**This submission demonstrates the edge tier's actual code path** (real
YOLOv8 + PaddleOCR, verified end-to-end — see HLD.md §5) at ~30-camera
scale, with the central-tier API/registry/RBAC layer built to the same
interface it would run at full scale, not a different mocked one.

### GPU accelerator estimate

- ~20 cameras/GPU (edge, mobile-scale models) → **80,000 / 20 ≈ 4,000 GPU-
  class edge inference units** statewide at full build-out.
- This is why a phased rollout (§6) matters: the pilot doesn't need to
  provision for 4,000 GPUs to prove the architecture works — it proves the
  *pattern* (one edge unit's software stack, replicated), and rollout
  scales unit count with camera count, not architecture.

### Re-ID similarity search at scale — a named unsolved problem, not glossed over

At full build-out, appearance embeddings accumulate fast: ~1 vehicle
event/sec/camera peak × 80,000 cameras ≈ tens of billions of embeddings
per day if retained at the hot-tier window (§4). Brute-force
nearest-neighbor search against that store for every new detection is not
tractable, and no Re-ID deployment at this scale does it that way. The
documented approach (not built this week, since it needs the district-
scale rollout in §6 to be worth building):

- **A dedicated vector index** (`pgvector` for moderate scale, or a
  purpose-built vector DB like Milvus at full scale) — PostGIS is a
  spatial extension, not a vector-similarity engine, and is not the right
  tool for embedding search.
- **Candidate filtering before similarity search, not after:** a new
  detection only searches embeddings from (a) cameras within plausible
  travel distance/time of where it was seen (§ occlusion-handling logic
  in the proposal's design, same principle as travel-time plausibility),
  and (b) a bounded recent time window. This turns an intractable
  full-store scan into a bounded regional/temporal lookup — the same
  reason regional Re-ID matching is placed at the **regional** tier (§2's
  table), not the central tier, in this architecture.

## 3. Network bandwidth planning

- **Camera → edge:** local/regional network only, video never leaves the
  region except for the specific live-view requests an operator actively
  opens ("pace your load" — already enforced in this build's
  `StreamManager`: only cameras being actively processed/viewed have open
  connections).
- **Edge → regional → central:** structured events only (§1's ~640 Mbps
  full-scale estimate), plus on-demand selective video relay (an operator
  viewing a specific camera's live feed, or pulling a specific incident's
  clip) — not a firehose.
- **Low-bandwidth sites** (rural/border districts explicitly called out in
  the problem statement — Valsad, Dahod, Dwarka): run detection/OCR at the
  edge unconditionally so only KB-scale events cross the low-bandwidth
  link, never raw frames. This is not a future optimization — it's the
  same architecture already used for the ~30-camera pilot, just phrased at
  scale.

## 4. Storage tiers

| Tier | Contents | Retention | Technology |
|---|---|---|---|
| Hot | Live event stream, active alerts, last N days of vehicle events | 7–15 days (matches existing departmental retention per HACKATHON_DETAILS.md §5) | PostgreSQL/PostGIS, indexed on plate + camera + timestamp |
| Warm | Historical events for investigation lookback | 90 days–1 year (case-dependent; purpose-bound queries against this tier are audit-logged the same as hot-tier queries) | Partitioned PostgreSQL tables or a columnar store (e.g. TimescaleDB) |
| Cold | Long-retention compliance archive; NOT raw video by default (see §1) — structured events + any specifically-preserved video for active cases | Per legal/case retention policy | Object storage (S3-compatible), lifecycle-tiered |

Video itself follows **each department's own existing retention** (7–15+
days, cloud or local per HACKATHON_DETAILS.md §5) — Sentinel does not take
over video storage, consistent with the "interoperability layer, not a
replacement VMS" pitch (STRATEGY.md).

## 5. Load balancing, horizontal scaling, monitoring, HA/DR

- **API tier:** stateless FastAPI instances behind a load balancer;
  horizontal scaling is adding instances, no code change required (no
  in-process state beyond the DB connection pool).
- **Stream-manager tier:** shard by camera ID range across instances; each
  instance's `StreamManager.reconcile()` logic already only opens workers
  for cameras assigned to it — sharding is a routing decision, not a
  rewrite.
- **Health monitoring:** already implemented for this submission's scale —
  each `RtspCameraWorker` reports `connected`/`last_frame_at`, synced into
  `CameraRegistry.is_healthy` (Model 1's health-monitoring deliverable) and
  surfaced via `GET /cameras/gap-analysis`. At full scale this feeds a
  standard metrics pipeline (Prometheus-style scrape per edge unit) rather
  than the current direct-DB-write loop — same signal, different transport.
- **HA/DR:** PostgreSQL primary/replica with automated failover; regional
  event stores replicate to the central tier asynchronously, so a regional
  outage doesn't lose central-tier watchlist/RBAC availability, only that
  region's fresh events until it recovers.
- **RBAC at scale:** the current API-key + role model
  (`ApiKeyEntry.department`) extends directly to department-scoped access
  control — a department's investigators see that department's cameras by
  default, escalating to cross-department queries only for roles
  explicitly granted it. Not built this week (single flat role set today),
  but the schema and dependency-injection pattern (`api/auth.py`) already
  supports adding the department-scope check without restructuring.
- **Backup:** distinct from the HA/DR failover above — automated daily
  PostgreSQL base backups plus continuous WAL archiving (standard
  Postgres practice, e.g. `pgBackRest`/`WAL-G`), retained per the same
  hot/warm/cold windows as §4's live data, stored in a separate
  availability zone/region from the primary so a backup isn't lost to the
  same failure it's meant to recover from. Not built for the pilot's
  single SQLite file — a `sqlite3 .backup` cron job is the pilot-scale
  equivalent, sufficient for a ~30-camera demo, not a production
  substitute for the above.
- **Encryption:** TLS for every network hop (camera→edge stays on the
  department's own trusted network per §3; edge→regional→central and all
  operator-facing traffic run over TLS). At rest: full-disk/volume
  encryption on the database and object-storage tiers (standard cloud
  provider disk encryption, or LUKS for on-prem), plus the existing
  application-level protection already built for this submission — API
  keys are stored as SHA-256 hashes, never plaintext (`api/auth.py`), and
  the sandbox's own camera credentials are never exposed to the browser,
  only proxied server-side (`routes_stream.py`).
- **Network segmentation:** edge units sit on each department's own
  network segment (no direct internet exposure); only the structured
  event stream and the specific live-view relay traffic cross into the
  regional/central tier, through a defined gateway — the same "camera
  video never leaves its region except for an actively-opened view"
  principle as §3, extended to network topology, not just bandwidth.
  Central-tier API and database sit in their own segment, reachable only
  through the API gateway, not directly from edge/regional networks.

## 6. Phased rollout

1. **Pilot (this submission):** ~30 real sandbox cameras, single-node
   deployment, SQLite → demonstrates the full pipeline end-to-end.
2. **District pilot:** one NETRAM-equivalent district, PostgreSQL, one edge
   GPU unit, real department onboarding via the bulk-import API.
3. **Regional rollout:** multiple districts, Kafka event bus introduced
   between edge and central tiers (documented architecture already in
   HLD.md §2, not deployed this week).
4. **Statewide:** all 26 departments, ~80,000 cameras, full edge-unit
   fleet per §2's GPU estimate, central tier horizontally scaled per §5.

Each phase reuses the same codebase — the pilot's `AnalyticsPipeline`,
`IdentityResolver`, and RBAC layer are the same classes that run at
district and statewide scale, just deployed with more instances and a
different `DATABASE_URL`. Nothing in this submission is a throwaway demo
architecture that would need to be rebuilt for production.

## 7. Cost estimate (rough, for planning discussion only)

| Item | Full-scale estimate | Basis |
|---|---|---|
| Edge GPU units | ~4,000 units (§2) | ~20 cameras/GPU |
| Central PostgreSQL cluster | Multi-TB, horizontally scaled | Hot+warm tier per §4 |
| Object storage (cold tier) | Scales with retained-case video, not full-fleet raw video | §4's default-no-raw-video policy |
| Network | Regional links sized for §3's ~640 Mbps event-plane estimate, not §1's 160 Gbps raw-video figure | §1/§3 |

These are magnitude estimates for a planning conversation, not a
procurement-ready budget — an actual cost model needs real department
camera counts, existing NETRAM infrastructure reuse potential, and vendor
GPU pricing at time of procurement, none of which are available to size
precisely during this hackathon submission.
