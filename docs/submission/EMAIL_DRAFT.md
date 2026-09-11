# Email Draft — Sentinel: Scalability & Architecture Response

**To:** Gujarat Police Innovation Challenge — Core Team
**Subject:** Sentinel — Scalability Plan, Architecture, and Positioning vs. Existing Infrastructure

---

Hello,

Following up on your questions about how Sentinel scales beyond the
hackathon and how it fits alongside Gujarat's existing CCTV
infrastructure — a summary below.

**What Sentinel is:** an open, vendor-neutral interoperability and
intelligence layer *designed* to sit above existing departmental CCTV/VMS
infrastructure — including systems like VISWAS/NETRAM/TRINETRA — rather
than replacing it. This submission demonstrates that architecture against
the hackathon's own sandbox feeds (RTSP/ONVIF-style ingestion, standard
protocols), not against a live VISWAS/NETRAM/TRINETRA connection we don't
have access to — the vendor-neutral, standards-based design is what makes
that integration feasible without a rebuild, not a claim that it's already
been proven against those specific systems. It registers cameras,
normalizes feeds into one event model, and correlates vehicle observations
**across departments**, and (as a design target, not built — see the
"query, don't copy" principle in the full HLD) connects to authorized
databases (VAHAN, CCTNS, eGujCop) without requiring any department to
change what they already run.

**Architecture:** a Model 1 + Model 2 hybrid (per the challenge's own
"combine suitable elements from two or more models" allowance) —
centralized camera registry/GIS/RBAC (Model 1) plus direct unified
viewing and AI analytics (Model 2), with a documented Model 3/4
(federation → central platform) roadmap for later, not claimed as built
now. The core design principle: centralize metadata and events, never
raw video. At 80,000 cameras, raw video would need ~160 Gbps sustained
(~1.7 PB/day) — not feasible for anyone. Structured events reduce this to
~640 Mbps statewide, a ~250x cut, which is what makes a real statewide
event plane achievable.

**Scaling path** (same codebase, not a rebuild at each stage): pilot
(~30 cameras, this submission) → district (PostgreSQL, one edge GPU
unit) → regional (Kafka event bus, async replication to central) →
statewide (all 26 departments, ~80,000 cameras).

**Why this adds value beyond what's already running:** TRINETRA/NETRAM/
VISWAS give operators eyes on cameras. Sentinel adds what a viewing
platform doesn't: cross-department vehicle identity resolution (one
timestamped movement history even across departments with no shared
VMS), graceful degradation when a plate can't be read (tracked by
appearance instead, upgraded retroactively the moment any camera reads
it), an explainable "why was this vehicle linked?" trail for every
cross-camera match, and purpose-bound audited queries with an enforced
retention policy — governance built into the code, not a checklist.

**Real-world grounding, not just a hackathon claim:** the UK's National
ANPR Service consolidated 44 disparate systems across 36 police forces
and 5 vendors into one national service (BAE Systems, live 2019) — the
same integration challenge Gujarat's 26 departments face. Gujarat's own
ICCC/Safe City network (Gandhinagar included) already runs the same
city→state→national tiering. And a real vehicle's real plate has now been read
correctly and confidently on live sandbox footage this week — verified
end-to-end through our actual production accept-logic, not a promising
OCR string in isolation.

Every current gap (WHEP low-latency preview, road-network routing,
cross-frame OCR consensus voting, full 80k-camera physical ingestion) is
documented honestly rather than hidden — happy to walk through the full
technical writeup (`HLD.md`/`SCALABILITY.md`) or the detailed briefing
(`ORGANIZER_BRIEFING.md`) if useful.

Happy to discuss further or join a call to go deeper on any part of this.

Best regards,
[Your name]
[Team/contact info]

---

*(Draft — edit tone/names/signature before sending. Full detail with
citations in `ORGANIZER_BRIEFING.md`.)*
