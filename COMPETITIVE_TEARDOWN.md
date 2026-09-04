# Competitive Teardown → Path to a Sellable Product

Synthesized 2026-09-03 from a public-source study of five incumbents
(Staqu, Videonetics, Vehant, Innefu, Palantir Gotham). Goal: understand
how they actually work, then map — under `STRATEGY.md`'s scope discipline —
what Sentinel can adopt now (cheap, hackathon-scope) vs. what belongs on a
post-hackathon commercialization roadmap.

## Source-quality caveat (read first)

Everything below is from **vendor marketing, product datasheets, and public
docs** — not independent benchmarks, not code, not decompilation. This is a
study of each company's *public technical footprint*, not literal reverse
engineering (their models/code are proprietary and were not accessed).
Treat throughput/accuracy/deployment numbers as vendor-reported. Never
repeat them to the jury as verified fact. This document is for **product
strategy**, not for citing performance claims.

## The most important finding, up front

**These incumbents' real moat is not their AI.** Detection/ANPR/tracking are
commodity in 2026 (we wired real YOLOv8+PaddleOCR+ByteTrack in days). Their
defensibility is three things a prototype does *not* have:

1. **Certifications that gate Indian government sales** — STQC (MeitY)
   software certification is already **required for GeM / government
   procurement of VMS software**; ISO 27001 (ISMS) adds bid-evaluation
   points and is increasingly mandatory; BIS-ER covers hardware; **ARAI-
   compliance** is what makes Vehant's automated challans *legally
   admissible*. ([STQC ISMS](https://www.stqc.gov.in/iso-27001-information-security-management-system-isms-certification), [India CCTV compliance 2026](https://arcisai.io/cctv-compliance-2026))
2. **Government backend integrations already live** — VAHAN / Sarthi / NIC
   e-Challan write-back (Vehant), multi-agency data fusion (Innefu).
3. **Deployment track record** — hundreds of live sites, which is its own
   procurement credential.

**Implication:** the road to "sellable" runs through certifications +
integrations + references, not more models. Sentinel's honest wedge is the
*open, explainable* architecture (STRATEGY.md's differentiation) — but that
wins pilots, not procurement, until the certification gates are cleared.
Say this plainly in any commercialization pitch; it's more credible than
claiming the tech alone is the moat.

---

## Per-company teardown (public technical footprint)

### Staqu — JARVIS
- **What it is:** audio+video analytics platform, markets 400k frames/sec
  across thousands of feeds, sub-second latency, any IP camera, 50+ use
  cases / 100+ analytics. Deploys cloud / on-prem / edge.
  ([staqu.com/what-is-jarvis](https://www.staqu.com/what-is-jarvis/))
- **The one clever ops feature worth stealing:** a **Streaming Agent that
  eliminates the need for a static IP at each site** — the edge pushes out
  to central, so no per-site public IP / inbound firewall rule / port
  forwarding. This is the unglamorous thing that makes multi-site rollout
  actually cheap, and it's a real gap for us (our `StreamManager` assumes it
  can reach each camera's RTSP URL — fine for the sandbox, painful across 26
  departments' NAT'd networks).
- **Take:** the reverse-connection / agent-push deployment model.

### Videonetics — Intelligent VMS 3.0 ("DeeperLook" framework)
- **What it is:** full VMS + a **configurable DNN framework** ("DeeperLook")
  deployable at central / on-prem / cloud / edge; ONVIF Profiles **S, G, T,
  M**; federated architecture where **compute nodes auto-register with
  minimal config**. ([Intelligent VMS 3.0 datasheet](https://www.videonetics.com/public/media/datasheet/Intelligent-VMS-3.0.pdf))
- **The scale pattern worth stealing:** **node auto-registration** into a
  federation. Our `SCALABILITY.md` §5 already proposes sharding by camera-ID
  across stream-manager instances — the missing piece is a node that boots,
  auto-registers, and claims a shard with no hand-config. That's the
  difference between "scales on paper" and "scales operationally."
- **Take:** auto-registering analytics/stream nodes; widen ONVIF target from
  S/T toward S/G/T/M over time.

### Vehant — VIDES
- **What it is:** edge GPU/CPU units, Indian-optimized ANPR OCR, **ARAI-
  compliant** enforcement, e-Challan + VAHAN/Sarthi NIC auto-challan
  write-back, ONVIF, "Make-in-India / highway-grade." ([vehant.com/products/vides](https://www.vehant.com/products/vides/))
- **The commercial lesson:** the value isn't the OCR — it's that a violation
  becomes a **legally-issued challan** via NIC integration, and ARAI
  certification is what makes that admissible. That's a licensing/
  certification play, not a CV play.
- **Take (roadmap, not now):** VAHAN/e-Challan *write-back* (we currently do
  "query, don't copy" — enforcement write-back is the commercial step up);
  pursue ARAI-compliance only if entering the enforcement market.

### Innefu — Prophecy / AI Vision
- **What it is:** an **intelligence-fusion** engine unifying CDR, ANPR, face,
  forensic, OSINT into one repository, with link-analysis / heatmaps and
  cross-agency coordination. ([innefu.com/intelligence-fusion-centre](https://innefu.com/intelligence-fusion-centre-a-comprehensive-guide/))
- **The lesson:** the high-margin product is the *fusion/investigation*
  layer above the sensors, not the sensors. This is the same direction our
  identity-resolution layer points — Innefu just fuses many more source
  types.
- **Take (roadmap):** generalize our vehicle-identity graph toward a
  multi-source *investigation* graph. **Boundary:** face recognition stays
  OUT (STRATEGY.md — DPDP/bias); CDR/OSINT fusion is a big commercial
  expansion, documented, not hackathon-scope.

### Palantir — Gotham (architecture north star, not a competitor to copy)
- **What it is:** a **dynamic ontology** — typed objects (person/place/event)
  + typed links → a governed knowledge graph — with **lifecycle state
  management** (e.g. Suspect → Investigated → Cleared) enforced across the
  platform. ([Palantir ontology explainer](https://pythonebasta.medium.com/understanding-palantirs-ontology-semantic-kinetic-and-dynamic-layers-explained-c1c25b39ea3c), [Gotham object/link types](https://www.palantir.com/docs/foundry/object-link-types/enable-gotham-integration))
- **What maps to us:** our `VehicleIdentity` ← `VehicleEvent` (observation)
  with `link_method`/`link_score` *is* a minimal ontology already. The two
  cheap, high-value ideas to borrow: (a) an explicit **entity lifecycle
  state**, and (b) **typed links** so the graph is queryable/explainable.

---

## The roadmap, split by scope discipline

### A. Cheap, high-value, arguably reachable now (hackathon-scope)
1. **Entity lifecycle state (from Palantir).** Add a status to a watchlist/
   vehicle entity — e.g. `flagged → located → cleared` — surfaced in the
   Alerts/Vehicle UI. Small schema + UI change; directly demoable; makes the
   "intelligence layer" claim concrete. **Best value/effort of anything here.**
2. **Explainable/typed link labels (from Palantir).** We already store
   `link_method`; exposing it as a small typed vocabulary in the API/UI (not
   free text) sharpens the explainability story at near-zero cost.

### B. Post-hackathon commercialization roadmap (document only)
3. **Agent-push / reverse-connection ingestion (from Staqu).** Removes the
   static-IP-per-site requirement — the real cost driver for 26-department
   rollout. Design note into `SCALABILITY.md`; prototype only post-hackathon.
4. **Auto-registering federation nodes (from Videonetics).** The missing
   operational piece under `SCALABILITY.md` §5's sharding design.
5. **VAHAN / e-Challan write-back + ARAI path (from Vehant).** The
   enforcement-revenue product; only if entering that market.
6. **Multi-source investigation graph (from Innefu).** Generalize the
   vehicle graph to more authorized sources (CDR/OSINT) — **not** face.
7. **Configurable analytics framework (from Videonetics DeeperLook).** Our
   pluggable-stub `Protocol` pattern is the seed; a no-code analytics-config
   layer is the productized evolution.

### C. The actual "sellable" gate — non-negotiable, none of it is code
8. **STQC software certification** (MeitY) — required for GeM/government VMS
   procurement.
9. **ISO 27001 (ISMS)** — bid-scoring points, increasingly mandatory; our
   existing RBAC + audit-log + retention design is the substantive
   groundwork, but certification is a process, not a feature.
10. **GeM listing** + **CERT-In security audit** + (for enforcement)
    **ARAI** + (for hardware) **BIS-ER**.
11. **Reference deployments** — a real district pilot is itself a
    procurement credential.

### Explicitly NOT chased (unchanged from STRATEGY.md)
- Face recognition / face re-ID (DPDP + bias) — even though Staqu/Innefu
  offer it.
- Replacing existing VMS / building a Model-4 super-platform.
- Cramming 50+ analytics use cases into the build window — depth on vehicle
  identity beats breadth for both the jury and a focused first product.

---

## Sources
- Staqu JARVIS: [what-is-jarvis](https://www.staqu.com/what-is-jarvis/), [platform blog](https://www.staqu.com/blog-jarvis-ai-video-analytics-platform/)
- Videonetics: [Intelligent VMS 3.0 datasheet](https://www.videonetics.com/public/media/datasheet/Intelligent-VMS-3.0.pdf), [intelligent-vms](https://www.videonetics.com/intelligent-vms)
- Vehant VIDES: [product page](https://www.vehant.com/products/vides/), [traffic-ai](https://www.vehant.com/traffic-ai/)
- Innefu: [intelligence fusion centre](https://innefu.com/intelligence-fusion-centre-a-comprehensive-guide/), [products](https://innefu.com/products/)
- Palantir Gotham: [ontology explainer](https://pythonebasta.medium.com/understanding-palantirs-ontology-semantic-kinetic-and-dynamic-layers-explained-c1c25b39ea3c), [object/link types](https://www.palantir.com/docs/foundry/object-link-types/enable-gotham-integration)
- Indian govt procurement gates: [STQC ISMS](https://www.stqc.gov.in/iso-27001-information-security-management-system-isms-certification), [India CCTV compliance 2026](https://arcisai.io/cctv-compliance-2026)

*All vendor claims above are marketing-sourced and not independently verified — see the caveat at the top.*
