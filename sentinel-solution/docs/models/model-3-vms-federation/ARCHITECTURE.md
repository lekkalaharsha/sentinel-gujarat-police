# Model 3 — VMS Federation & Middleware Integration — Architecture

**Status: built and verified 2026-09-11.** This document now describes
real, running code — verified against the real accumulated `sentinel.db`,
a real 2,000-row NYC Open Data slice, and a full backend regression suite
(70/70 passing, including 15 new Model-3-specific tests). See
`IMPLEMENTATION_PLAN.md`'s per-step checkmarks for exactly what was
built and how it was verified. This section is now ground-truthed like
the Model 1/2 docs in this folder tree, not a pre-build prediction.

## Why federation, and why it's honestly scoped down

Model 3's spec text (`docs/hackathon/HACKATHON_DETAILS.md` §7) asks for
"a middleware layer integrating multiple departmental VMS platforms while
departments retain independent infrastructure" — federating **≥2
systems**. We have exactly one real system to federate: the Sentinel
sandbox already integrated by Model 1/2. There is no second government
VMS available to us. **Revised 2026-09-11** (user rejected the original
self-authored-fixture plan): building this honestly, without fabricating
data, means:

- **System A** is our existing, real Model 1/2 stack — the sandbox's 30
  cameras, already ingested via `CameraRegistry` + `VehicleEvent`. This
  already is a real "departmental VMS" in the spec's sense.
- **System B** is **NYC's public "Open Parking and Camera Violations"
  dataset** (`data.cityofnewyork.us`, also mirrored on `catalog.data.gov`)
  — a real, official, record-level government open dataset (~10M
  records/year, public domain, no reuse restriction) with a genuinely
  different schema than ours: `Plate ID`/`Registration State`/`Plate
  Type`, split `Issue Date`+`Violation Time` fields, and a
  precinct/street-code location model instead of our lat/lon+camera_id.
  Plates are present and not anonymized (it's a public administrative
  record), so this is real data, not a fixture we wrote — see
  `RESEARCH.md`'s "System B dataset selection" section for the full
  evaluation of alternatives and why this one was chosen.
  **Residual honesty caveat, must stay visible everywhere this surfaces:**
  there is **zero real cross-system plate overlap** — different country,
  different vehicle population, no possible genuine match. The federation
  demo therefore proves the adapter/normalization + correlation-engine
  *mechanics* work on two real, independently-formatted data sources, not
  that a specific real vehicle was recovered across both systems. If the
  demo needs to show a populated correlation result (not just "zero
  matches, as expected"), that one specific correlated example must be a
  deliberately-constructed, clearly-labeled synthetic overlay on top of
  the two real datasets — call this out explicitly at the point it's
  shown, not just in this doc. This is not a second real government VMS
  in the Gujarat departmental sense, and must never be presented as one —
  it's a real, independent, differently-formatted public dataset used to
  demonstrate genuine format-heterogeneity handling.

## Component diagram (target)

```text
┌────────────────────────────┐   ┌──────────────────────────────────┐
│ System A: Sentinel stack    │   │ System B: NYC Open Parking &      │
│ (real — Model 1/2, already  │   │ Camera Violations dataset (real,  │
│  built, this is not new)    │   │ public, data.cityofnewyork.org —  │
│                              │   │ clearly labeled as an independent │
│                              │   │ real dataset, NOT a Gujarat dept  │
│                              │   │ VMS, in all UI/docs)              │
└──────────────┬───────────────┘   └──────────────┬─────────────────────┘
              ▼                                  ▼
┌──────────────────────────────┐   ┌──────────────────────────────────┐
│ SentinelAdapter                │   │ NycOpenDataAdapter                │
│ (VMSAdapter Protocol impl,     │   │ (VMSAdapter Protocol impl, parses  │
│  wraps existing VehicleEvent   │   │  the real NYC CSV export, maps its │
│  query — no new ingestion)     │   │  Plate ID/Issue Date/Violation     │
│                                 │   │  Time/precinct fields to the same │
│                                 │   │  NormalizedEvent shape)            │
└──────────────┬───────────────────┘   └──────────────┬─────────────────────┘
              └──────────────────┬─────────────────────┘
                                 ▼
              ┌──────────────────────────────────────┐
              │ FederatedEvent table (additive)        │
              │ id, source_system, plate, observed_at, │
              │ raw_payload_json — normalized landing   │
              │ zone for both adapters, polling ingest  │
              └──────────────────┬─────────────────────┘
                                 ▼
              ┌──────────────────────────────────────┐
              │ Correlation query (routes_federation.py)│
              │ GROUP BY plate within a time window,    │
              │ HAVING >1 distinct source_system —      │
              │ produces plate/sources/time_gap_s/       │
              │ correlation_confidence, reusing Model    │
              │ 2's link_score/link_time_gap_s vocabulary│
              └──────────────────┬─────────────────────┘
                                 ▼
              ┌──────────────────────────────────────┐
              │ FederationDashboard.jsx                │
              │ table of correlated plates, click-      │
              │ through to existing VehicleTimeline.jsx │
              └──────────────────────────────────────┘
```

## Adapter interface (Protocol-based, matches existing stub/real pattern)

```python
class VMSAdapter(Protocol):
    def fetch_events(self, since: datetime) -> list[NormalizedEvent]: ...

@dataclass
class NormalizedEvent:
    plate: str
    observed_at: datetime
    camera_id: str
    source_system: str   # "sentinel" | "nyc_open_data"
    raw_payload: dict
```

This is the literal "adapter/plugin architecture for multiple vendors"
deliverable — `SentinelAdapter` and `NycOpenDataAdapter` are two
implementations of one `Protocol`, following the same pattern already
used for `analytics/detector.py`'s detector interface. Adding a real
third system later (a genuine second government VMS, if sandbox access
is ever granted, or another public dataset) means writing one more
`VMSAdapter` implementation — no change to the correlation engine or
dashboard.

## What this deliberately is not

- **Not a message bus.** No Kafka/RabbitMQ. `FederatedEvent` is a polled,
  additive SQLite table — correlation is a batch SQL query on a time
  window, not real-time stream processing. Call it a "federation ingest
  and correlation pass," not an event bus, in every doc and demo.
- **Not a second Gujarat departmental VMS integration.** System B is a
  real, independent, public dataset from a different country/domain,
  used to demonstrate genuine format-heterogeneity handling — not a
  second real government VMS in the spec's departmental sense, and never
  presented as one. There is zero real plate overlap with the sandbox by
  construction (see `ARCHITECTURE.md`'s honesty caveat above) — any
  populated correlation example shown in a demo must be a clearly-labeled
  synthetic overlay, not implied to be a genuine cross-system recovery.
  **That overlay now exists as System C** (`demo_partner_vms`,
  `DemoPartnerVmsAdapter`, built 2026-09-11): hand-written partner
  sightings of plates Sentinel really read, so the correlation engine can
  be exercised end-to-end instead of only by unit tests. It is labelled
  everywhere it surfaces — a self-describing `source_system` id, an
  `involves_synthetic_source` flag on every correlation, a "Basis" column
  reading `SYNTHETIC` in the PDF, and the expanded `HONESTY_NOTE`. Systems
  A and B remain untouched real data, and still correlate with nothing.
- **Not the Model 2 direct-connect path re-labeled.** Model 2 already
  connects directly to the one real sandbox; Model 3's value-add is the
  *normalization + cross-system correlation* layer sitting above two (or
  more) independently-formatted event sources — that's what makes it a
  federation/middleware layer per Q19's Model 2-vs-3 distinction, not
  just "the same thing with an extra table."

See `IMPLEMENTATION_PLAN.md` for the scoped build plan and
`REQUIREMENTS.md` for the literal spec-to-plan mapping.
