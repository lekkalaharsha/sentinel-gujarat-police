# Model 3 — Research Notes

External precedent for the adapter/federation design in `ARCHITECTURE.md`.
Compiled 2026-09-11, before any Model 3 code exists — this grounds the
design in real standards/projects, not invented ones.

## Interoperability standard: ONVIF Profile S/G/M

ONVIF is the real, vendor-neutral standard for exactly this kind of
normalization boundary:

- **Profile S** — live streaming/PTZ control.
- **Profile G** — recording/storage/export.
- **Profile M** — metadata/analytics conformance (vehicle, plate, face
  metadata events).

A real ONVIF-conformant deployment already solves "many vendor formats →
one normalized event schema" at the protocol level — a camera/VMS emits
ONVIF events, and any ONVIF client consumes a common schema regardless of
vendor. This is the standards precedent for *why* an adapter-normalization
layer (our `VMSAdapter` Protocol → `NormalizedEvent`) is the architecturally
correct pattern for Model 3, not an invented approach. It is **not**
something we integrate directly — the sandbox exposes no ONVIF endpoint
(same honest caveat already recorded in Model 1/2's docs) — so our
adapters normalize proprietary/simulated formats in application code
instead of via ONVIF itself.

## Open-source VMS precedent for adapter/plugin patterns

- **ZoneMinder** and **Shinobi** are real, actively-referenced open-source
  VMS/NVR projects that already solve "one internal event/recording model,
  many source-camera drivers" — Shinobi's per-camera "monitor" abstraction
  and ZoneMinder's multiple capture-driver support are the same shape of
  problem as our `VMSAdapter` Protocol, at smaller scale. Cited here as
  precedent for the *pattern*, not as a dependency — we are not embedding
  either project.
- **MediaMTX**, already documented elsewhere in this repo (`STRATEGY.md`,
  `HLD.md`) as the production-path media relay, is relevant precedent for
  protocol-adapter thinking generally but is not itself an event-
  correlation tool — it operates at the media-relay layer, not the
  metadata-correlation layer Model 3 needs.

## Why the "metadata exchange bus" is a table, not Kafka, this pass

The literal spec's suggested stack lists Kafka/RabbitMQ. At our real
scale — one live system + one fixture, a handful of federated events per
demo run — a message bus adds operational surface (a broker to run, a
consumer-group lag concern, a serialization format to pick) with no
corresponding capability win. A polled `FederatedEvent` table achieves
the same logical outcome (asynchronous ingestion from independent
adapters, queryable afterward) with zero new infrastructure, consistent
with how Model 1/2 already deferred Kafka/Elasticsearch for the same
pilot-scale reasoning (see Model 2's `ARCHITECTURE.md` stack-deviation
table). `SCALABILITY.md` already documents Kafka as the correct district/
state-tier upgrade — Model 3 should cross-reference that section once
built, not re-argue the case for a bus from scratch.

## Correlation-engine design precedent

There is no need to look outside this codebase for the correlation
design — Model 2 already solved the closely analogous problem of linking
independently-observed signals (per-camera OCR reads, appearance
embeddings) into one identity with an explainable score
(`link_method`/`link_score`/`link_time_gap_s` on `VehicleEvent`). Model
3's cross-system correlation is the same shape of problem one level up
(independently-formatted *systems* instead of independently-timed
*cameras*), so reusing that vocabulary and the same "explainable score,
not a black box" principle keeps the two models architecturally
consistent rather than inventing a second correlation philosophy.

## System B dataset selection — superseded 2026-09-11

An earlier draft of this document proposed a self-authored CSV fixture as
System B. **The user rejected this** — a jury asking "what's the second
system?" deserves a better answer than "a file we wrote." Independent
research (2026-09-11) evaluated real, public candidates against four
criteria: genuinely public/accessible, event-like (plate+timestamp+
location, not just images), a genuinely different schema from ours, and
usable without needing us to fabricate fields.

**Candidates evaluated:**

- **NYC Open Data — "Open Parking and Camera Violations"**
  (`data.cityofnewyork.us`, mirrored on `catalog.data.gov`). Real,
  official government open dataset, ~10M records/year, public domain, no
  reuse restriction. Fields: `Plate ID`, `Registration State`, `Plate
  Type`, split `Issue Date`+`Violation Time`, `Violation Precinct`/street
  location, vehicle make/color/body type/year. Plates present, not
  anonymized (public administrative record). **Selected** — the only
  candidate meeting all four criteria without adaptation.
- **UFPR-ALPR** (academic ANPR dataset, Brazil,
  `github.com/raysonlaroca/ufpr-alpr-dataset`) — real and well-known, but
  image+annotation pairs with no timestamp field, and license is
  academic/non-commercial-only, a fit concern for a hackathon submission.
  Would need synthesized timestamps to become "events" — reintroduces the
  fabrication problem. Not selected.
- **Kaggle "Indian Traffic E-Challan Daily Dataset (2015–2026)"** —
  provenance questionable (date range extends into the future for a
  supposedly historical dataset, suggesting a synthetically generated
  practice dataset, not authoritative government records). Not selected.
- **data.gov.in traffic/challan datasets** — real Indian government open
  data, but the available challan datasets are aggregated statistics
  (counts by year/month/state/city), not record-level data with plates.
  India generally doesn't publish record-level ANPR data with plates
  publicly, unlike NYC. Not selected.

**The residual honesty caveat that survives this change:** even with a
real dataset, there is zero genuine plate overlap between NYC vehicles
and the Gujarat sandbox's vehicles — different countries, disjoint
populations. This doesn't undermine the deliverable (adapter/plugin
architecture + event-correlation engine + dashboard are all real,
working code, tested against two real, independently-formatted data
sources), but it does mean a demo showing a *populated* correlated match
needs one clearly-labeled synthetic overlay example — see
`ARCHITECTURE.md`'s caveat, which must travel with the sample report and
dashboard wherever they're shown.
