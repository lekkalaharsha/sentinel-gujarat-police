# `demo_partner_vms_seed.csv` — SYNTHETIC. Not real data.

**Every row in this file was written by hand. It is not a real dataset, it is
not a real VMS export, and no vehicle in it was actually observed by a partner
system.** It is loaded under the source system id `demo_partner_vms`, which is
named so that it can never be mistaken for a real departmental feed in any API
response, dashboard, or PDF report.

## Why it exists

Model 3's correlation engine joins a plate seen by two *different* source
systems within `SENTINEL_FEDERATION_CORRELATION_WINDOW_S`. The two real sources
we federate — Sentinel's own Model 1/2 stack and NYC Open Data's "Open Parking
and Camera Violations" — have **zero plate overlap by construction** (different
countries) and are three years apart in time. That is honest, and it stays
honest: the NYC fixture is untouched real data.

But it also means the correlation path could only ever be exercised by unit
tests, never end-to-end against the live database. This fixture closes that gap:
it gives the real correlation code real rows to join against, so the pipeline
can be demonstrated working rather than only asserted to work.

## How the plates were chosen

The `vehicle_number` values are **real plates that Sentinel's own ANPR pipeline
actually read** from real sandbox footage — they are already present in
`federated_event` under `source_system='sentinel'`. Only the *partner-side
sighting* is synthetic. Timestamps are offset from the real Sentinel sighting:

| Plate | Offset from real sighting | Expected result |
|---|---|---|
| `GJ01KH0099` | +47 s | correlates (high confidence) |
| `GJ09BA7548` | +128 s | correlates |
| `GJ32B2040` | +212 s | correlates |
| `GJ27ED1763` | +284 s | correlates (just inside the 300 s window) |
| `GJ08BF6165` | **+900 s** | **must NOT correlate** — deliberately outside the window, so the report proves the gate rejects as well as accepts |

`GJ01AB1234` is deliberately left out entirely, so the report also shows a
Sentinel plate with no partner sighting at all.

## Native format (deliberately a third schema)

This file uses field names and a timestamp representation that match **neither**
of the other two sources, so the adapter layer is exercised against three
genuinely different schemas rather than two:

| Source | Plate field | Time representation | Location field |
|---|---|---|---|
| `sentinel` | `plate` | ISO `datetime` column | `camera_id` |
| `nyc_open_data` | `plate` | split `issue_date` + `violation_time` (`MM/DD/YYYY` + `HH:MMA/P`) | `precinct` |
| `demo_partner_vms` | `vehicle_number` | **epoch milliseconds (UTC)** | `site_code` |

## Rules for using this file

- Never describe `demo_partner_vms` as a real system, a partner agency, or a
  Gujarat departmental VMS in any demo, slide, report, or conversation.
- The correlations it produces demonstrate that **the pipeline works**. They do
  **not** demonstrate that a vehicle was really seen by two agencies.
- To disable it entirely, unset `SENTINEL_DEMO_PARTNER_FIXTURE_PATH` or delete
  this file — `main.py` skips the adapter when the path does not exist, exactly
  as it does for the NYC fixture.
