# Model 3 — Requirements Coverage

Every bullet below is copied from the official challenge problem
statement's Model 3 section (`docs/hackathon/HACKATHON_DETAILS.md` §7,
plus Q18/Q19 from the clarifications). **Status: built and verified
2026-09-11** — ground-truthed against real, running code and a passing
regression suite, same standard as the Model 1/2 requirements docs in
this folder tree (this document originally described a pre-build plan;
it's now updated post-build).

Official spec text:

> Interoperability layer enabling cross-platform communication while
> departments retain independent infrastructure. Uses intermediate
> federation layers (vs. Model 2's direct connection).

> Q18: A middleware layer integrating multiple departmental VMS platforms
> while departments retain independent infrastructure.
> Q19: Model 3 uses intermediate federation layers; Model 2 connects
> directly to departmental systems.

## Key functional features

| Requirement | Status | Evidence |
|---|---|---|
| Adapter/plugin architecture for multiple vendors | ✅ **Built** | `VMSAdapter` Protocol + `NormalizedEvent` dataclass (`analytics/federation.py`), two real concrete adapters: `SentinelAdapter` (wraps existing `VehicleEvent` data) and `NycOpenDataAdapter` (parses a real public dataset) — see `ARCHITECTURE.md` |
| Metadata exchange bus | ✅ **Built — scoped down, not a real bus** | A polled `FederatedEvent` table (`ingest_all()`, idempotent by dedup key), not Kafka/RabbitMQ. This is the one deliberate downgrade from the literal spec's suggested stack — see `RESEARCH.md`'s reasoning |
| Event-correlation engine | ✅ **Built** | `_compute_correlations()` (`routes_federation.py`) — groups `FederatedEvent` rows by plate, finds the closest cross-source pair within a configurable window, reusing Model 2's `link_score` explainability vocabulary. Regression-tested for the within-window, outside-window, and same-source-doesn't-count cases |
| Unified workflow dashboard | ✅ **Built** | `FederationDashboard.jsx`, reusing existing table/click-through patterns from `GapAnalysisPanel.jsx`/`SearchView.jsx` |
| Extensible connector framework | ✅ **Built** | Same `VMSAdapter` Protocol — adding a system is one new adapter class, no change to correlation/dashboard |

## Expected deliverables

| Deliverable | Status | Evidence |
|---|---|---|
| Working middleware federating ≥2 systems | ✅ **Built — 2 real, independently-formatted data sources** (+1 clearly-labelled synthetic), not 2 live government VMS platforms | System A = real Sentinel stack; System B = NYC's real, public "Open Parking and Camera Violations" open dataset (`data.cityofnewyork.us`, a real 2,000-row slice downloaded live and checked into `scripts/fixtures/`). Zero real plate overlap between the two by construction (different countries), empirically confirmed (0 correlated plates against 1,100 real federated events). **System C (`demo_partner_vms`, added 2026-09-11) is synthetic** — hand-written partner sightings of plates Sentinel really read, added so the correlation engine runs end-to-end rather than only in unit tests. Verified against the live DB: 1,105 federated events, 3 sources, **4 correlations (gaps 47/128/212/284 s), each flagged `involves_synthetic_source: true`**, and a deliberate +900 s row correctly rejected by the window gate — see `ARCHITECTURE.md`'s honesty caveat |
| Unified event-correlation dashboard | ✅ **Built** | `FederationDashboard.jsx` + `GET /federation/correlations`, `investigator`+ role-gated |
| Adapter architecture documentation | ✅ **Built** | This document + `ARCHITECTURE.md`, finalized against the real, built code |
| Sample federated analytics report | ✅ **Built** | `GET /federation/correlations/export.pdf`, reusing the `reportlab` pattern from Model 1's gap-analysis PDF; a real sample generated end-to-end and checked into `docs/assets/sample_federation_report.pdf` |

## What "honestly scoped down" means here, explicitly

Two things diverge from the literal spec and must stay visibly flagged,
not quietly minimized, once built:

1. **Neither federated source is a second Gujarat departmental VMS.**
   System A is our real sandbox integration; System B is a real, public,
   independently-formatted government dataset from a different country
   and domain, not fabricated but also not what a jury would picture when
   reading "departmental VMS platforms." Every place this is shown —
   dashboard UI, sample report, submission docs — must label System B as
   an independent public dataset, not a second departmental VMS, and must
   disclose the zero-real-overlap caveat wherever a correlation result is
   shown. This mirrors this repo's existing rule for stubbed ML
   components: never claim a capability that isn't wired in as claimed.
2. **The "metadata exchange bus" is a polled table, not a message
   queue.** This is a deliberate pilot-scale decision (per
   `STRATEGY.md`'s scope discipline: no new infrastructure this week),
   not an oversight. `SCALABILITY.md`'s district/state-tier section is
   where a real Kafka/RabbitMQ bus belongs, and should be cross-
   referenced once Model 3 is built.

Neither of these blocks meeting the literal deliverable text — "working
middleware federating ≥2 systems" is met by two adapters, both real, and
a real correlation engine. The honesty obligation is disclosing what kind
of "system" each one is, not scope expansion to acquire a second live
Gujarat departmental VMS we don't have access to.
The honesty obligation is disclosure, not scope expansion to acquire a
second real government VMS we don't have access to.
