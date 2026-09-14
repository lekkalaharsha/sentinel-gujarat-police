# Model 3 — Implementation Plan

**Status: built 2026-09-11.** The user gave explicit go-ahead to start
the build (having confirmed Model 1/2's P0/P1 items don't block it — the
remaining `TASKS.md` P0 item, the own-feed demo video, is independent of
this work). Every step below is checked off against what was actually
built and verified — not a prediction anymore. Effort estimates below are
what was actually spent, not a forecast.

## Build order

### Step 1 — Adapter interface + real System-A adapter ✅

- [x] `analytics/federation.py`: `VMSAdapter` Protocol, `NormalizedEvent`
      dataclass.
- [x] `SentinelAdapter(VMSAdapter)` — wraps existing `VehicleEvent` query
      (`fetch_events(since)` → filters `observed_at >= since` AND
      `plate IS NOT NULL`, maps to `NormalizedEvent(source_system=
      "sentinel", ...)`). No new ingestion — reads data Model 2 already
      collects. Excludes unread (`plate=None`) events by design — same
      untrusted-input discipline as the rest of the pipeline (regression-
      tested).

### Step 2 — Real System-B adapter: NYC Open Parking and Camera Violations ✅

- [x] Downloaded a real 2,000-row slice of NYC Open Data's "Open Parking
      and Camera Violations" dataset live from its public Socrata API
      (`data.cityofnewyork.us/resource/nc67-uf89.csv`) and checked it into
      `scripts/fixtures/nyc_open_parking_sample.csv`, with provenance
      recorded in the sibling `nyc_open_parking_sample.README.md` (source
      URL, download date, license, the zero-overlap honesty caveat).
      **Real public data, not a fixture we authored.**
- [x] `NycOpenDataAdapter(VMSAdapter)` — parses the CSV, maps `plate`/
      split `issue_date`+`violation_time` (12-hour, AM/PM-suffixed,
      regression-tested including the 12A/12P edge cases)/`precinct` into
      `NormalizedEvent(source_system="nyc_open_data", camera_id=
      "precinct-<n>", ...)`. Unparseable rows are skipped, not guessed at
      (regression-tested). The module docstring and every downstream
      surface (route file, dashboard, PDF report) carry the "NOT a
      Gujarat departmental VMS" + zero-real-overlap caveat.

### Step 3 — Federated ingest + storage ✅

- [x] `FederatedEvent` model in `db/models.py` (id, source_system, plate,
      observed_at, camera_id, raw_payload_json, ingested_at) — a brand
      new table, so no `_ADDITIVE_MIGRATIONS` entry was needed
      (`create_all` builds new tables directly; verified against the real
      accumulated `sentinel.db` via `init_db()`, no errors, no data loss).
- [x] `ingest_all()` (`analytics/federation.py`) — idempotent by
      `(source_system, plate, observed_at, camera_id)` dedup key, so
      repeated polls over the same data never duplicate rows (regression-
      tested: identical adapter set run twice inserts 2 then 0 rows).
      Wired into `main.py`'s `federation_ingest_loop` (same
      daemon-thread-with-try/except pattern as the existing
      `retention_loop`), polling every `SENTINEL_FEDERATION_INGEST_INTERVAL_S`
      (default 120s). Falls back to Sentinel-only ingestion with a logged
      warning if the NYC fixture file is missing — same honest-fallback
      pattern as the ML component builders in `main.py`.

### Step 4 — Correlation engine + endpoint ✅

- [x] `routes_federation.py` (`APIRouter`, flat non-versioned prefix
      `/federation`): `GET /federation/correlations` — groups
      `FederatedEvent` rows by plate, finds the closest cross-source pair
      within `SENTINEL_FEDERATION_CORRELATION_WINDOW_S` (default 300s),
      computes `time_gap_s` and `correlation_confidence` (inverse of time
      gap, mirroring Model 2's `link_score` design). Regression-tested:
      correlates within the window, ignores matches outside it, and
      — the case that would have made this a trivial same-source dedup
      bug — ignores two sightings from the SAME source_system even when
      they share a plate and are close in time.
- [x] `investigator`+ role gate (`require_role`), same precedent as Model
      1's gap-analysis.

### Step 5 — Dashboard ✅

- [x] `FederationDashboard.jsx` — stats row (federated events, sources
      present, correlated-plate count), the backend's `honesty_note`
      rendered directly (not paraphrased in the frontend, so it can't
      drift from the backend's actual wording), a correlated-plates table
      with click-through to the existing vehicle-timeline view (reusing
      `App.jsx`'s existing `openVehicle` callback — same pattern
      `SearchView.jsx` uses), and a PDF export button. Added to
      `Sidebar.jsx`'s existing nav structure ("Federation (Model 3)"
      under Monitoring) and `App.jsx`'s existing view-switch, not a new
      top-level app shell. `npm run build`/`npm run lint` both clean (no
      new warning classes beyond ones already present elsewhere in the
      codebase, e.g. the pre-existing `set-state-in-effect` pattern also
      seen in `GapAnalysisPanel.jsx`).

### Step 6 — Sample federated report ✅

- [x] `GET /federation/correlations/export.pdf`, reusing the `reportlab`
      pattern from Model 1's gap-analysis PDF — same library, no new
      dependency. Generated one real sample report end-to-end against the
      real accumulated Sentinel data + the real NYC fixture (1,100 total
      federated events ingested) and checked it into
      `docs/assets/sample_federation_report.pdf`.
      **Result: 0 correlated plates** — the honestly-predicted outcome
      from `ARCHITECTURE.md`'s caveat, now empirically confirmed, not
      just theorized. No synthetic overlay example was added — the
      report states "(none — expected, given zero real cross-system
      plate overlap)" rather than fabricating a populated row; a
      synthetic demo example remains a possible future addition if the
      user wants one for presentation purposes, but wasn't added
      unprompted.

### Step 7 — Docs + tests ✅

- [x] `tests/test_federation.py` (15 tests): adapter mapping correctness
      (both adapters, including 12-hour-clock edge cases and unparseable-
      row handling), unread-plate exclusion, idempotent ingest, all three
      correlation-engine cases above, the honesty-note content, and PDF
      export (including the empty-correlations case, mirroring the real
      bug class Model 1's gap-analysis PDF test caught for an analogous
      empty-list branch). **Full backend suite: 70/70 passed** (55
      pre-existing + 15 new), run against the actual test runner, not
      assumed.
- [x] `ARCHITECTURE.md`/`REQUIREMENTS.md`/`RESEARCH.md` in this folder
      finalized against what was actually built — no divergence from this
      plan occurred (System B ended up exactly as scoped: real NYC data,
      zero real overlap, disclosed everywhere).
- [ ] `docs/hackathon/REQUIREMENTS_COVERAGE.md`'s "C. Model 3" section —
      not yet added, next step.

## Explicitly not doing

- Kafka/RabbitMQ message bus — see `RESEARCH.md`'s reasoning; `FederatedEvent`
  is polled, not streamed.
- A second real Gujarat departmental VMS integration — System B is a
  real, independent public dataset (NYC Open Data), not a second
  government VMS, until real access to a second departmental system
  exists.
- Kong/NGINX API Gateway — unnecessary at one-FastAPI-process scale; this
  repo has no API gateway anywhere today and Model 3 doesn't need to be
  the first place one appears.
- Redis — no caching need at this data volume; would be new
  infrastructure with no demonstrated requirement, same objection as
  Kafka.

## Go/no-go checklist before starting Step 1

- [x] **Corrected and resolved 2026-09-11.** An earlier pass of this
      checklist incorrectly recorded the user as having approved a
      self-authored-CSV-fixture premise; that was wrong — the user
      rejected it ("scope it differently") and specified System B should
      be a real, publicly available dataset with a genuinely different
      schema. Research found NYC's real "Open Parking and Camera
      Violations" open dataset as the best fit (see `RESEARCH.md`'s
      "System B dataset selection"); `ARCHITECTURE.md`, `REQUIREMENTS.md`,
      and this plan's Step 2 have been revised accordingly. Design premise
      is now: System A = real Sentinel stack, System B = real NYC public
      dataset, zero real cross-system plate overlap by construction
      (disclosed everywhere a correlation result surfaces).
- [x] **Resolved 2026-09-11.** User gave explicit go-ahead ("go ahead and
      start the Model 3 build") without conditioning it on the demo-video
      P0 item finishing first — treated as confirmation that sequencing
      concern is satisfied.

## Post-build note

Built and verified 2026-09-11: real System-A/System-B adapters, idempotent
polled ingest, correlation engine, dashboard, PDF export, 15 new
regression tests (70/70 backend suite passing), a real sample report
generated end-to-end (0 correlated plates — the honestly-predicted
outcome, now empirically confirmed). Not yet done: updating
`docs/hackathon/REQUIREMENTS_COVERAGE.md` with a "C. Model 3" section, and
tagging (`v0.4.0` per the original TASKS.md plan) — both pending user
review of this build.
