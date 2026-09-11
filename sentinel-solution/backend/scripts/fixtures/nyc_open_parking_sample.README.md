# `nyc_open_parking_sample.csv` — provenance

**Real, public, third-party data** — used as Model 3's "System B" for the
VMS-federation demo (`docs/hackathon/HACKATHON_DETAILS.md` §7's "≥2
systems" deliverable). Not fabricated, not a Gujarat departmental system.
See `sentinel-solution/docs/models/model-3-vms-federation/RESEARCH.md`'s
"System B dataset selection" for why this dataset was chosen over the
alternatives considered.

- **Source:** NYC Open Data — "Open Parking and Camera Violations"
  (dataset id `nc67-uf89`), `https://data.cityofnewyork.us/resource/nc67-uf89.csv`
- **License:** NYC Open Data — public domain, unrestricted reuse.
- **Downloaded:** 2026-09-11, via the dataset's public Socrata API
  (`$limit=2000`, columns: `plate,state,license_type,summons_number,
  issue_date,violation_time,violation,precinct,county,issuing_agency`).
- **This is a 2,000-row slice of a ~10M-record/year dataset** — enough for
  a demo, not the full dataset.

**Honesty caveat (must travel with every use of this file):** there is
zero real plate overlap between these NYC records and Sentinel's Gujarat
sandbox vehicles — different countries, disjoint vehicle populations. Any
correlation the federation demo produces against this data is either (a)
genuinely zero real cross-system matches, which is the expected, honest
result, or (b) one deliberately-constructed synthetic example layered on
top for demo purposes, which must be labeled as such wherever shown — see
`ARCHITECTURE.md`'s and `IMPLEMENTATION_PLAN.md`'s callouts in the
`model-3-vms-federation` docs folder.
