# Handoff prompt — deferred fixes for Sentinel (Gujarat Police hackathon)

Copy everything below the `---` into a fresh session with whichever coding
tool is picking this up (Codex, another Claude Code session, a teammate).
It's self-contained — no prior conversation context assumed.

---

## Project context

You're working on **Sentinel**, a submission for the Gujarat Police
Innovation Challenge 2026 hackathon: an interoperability layer over
Gujarat's CCTV infrastructure — camera registry + GIS (Model 1) and
unified viewing/analytics (Model 2), with vehicle plate tracking,
watchlist alerting, and cross-camera identity resolution as the core demo.

Working directory: the `sentinel-solution/` folder at the repo root.
Backend is FastAPI + SQLAlchemy/SQLite (`sentinel-solution/backend/app/`),
frontend is React/Vite (`sentinel-solution/frontend/src/`).

**Read these first, in order, before writing any code:**
1. `CLAUDE.md` (repo root) — project rules: every real capability ships
   with an honest stub, never claim a capability that isn't wired in,
   verify runtime behavior not just syntax, scope discipline (check
   `STRATEGY.md`'s explicit OUT list before adding anything).
2. `sentinel-solution/HLD.md` — the technical design doc, including §10
   "Known gaps" which lists everything already deliberately deferred.
   Don't re-fix or re-flag anything already listed there.
3. `sentinel-solution/REVIEW_FINDINGS.md` — a three-lens (software/ML/
   security) code review done 2026-09-04. Most findings are already fixed
   and verified; this handoff covers only the ones that weren't, because
   they need more than a quick fix.

**Deadline context:** Phase 1 submission deadline is 2026-09-15 (moved from
2026-09-07, confirmed 2026-09-05 via the live schedule page). Treat
remaining time as scarce. Each task below is independent — pick whichever
fits the time available, don't feel obliged to do all of them.

## Task 1 — Empirically justify the Re-ID similarity threshold (ML-3)

**File:** `sentinel-solution/backend/app/analytics/identity.py`,
`EMBEDDING_SIMILARITY_THRESHOLD = 0.80`.

**The problem:** this threshold gates whether two vehicle sightings at
different cameras, with no shared plate read, get merged into the same
cross-camera identity, based on cosine similarity between
`ColorHistogramEncoder` embeddings (`analytics/reid.py` — a 48-dim
HSV-histogram + grayscale-template vector, not a deep embedding). The
0.80 number has no empirical basis — nobody has measured what fraction of
genuinely-different vehicles score above it (false positives) or what
fraction of genuinely-same vehicles score below it (false negatives).

**What to do:**
1. Collect a labeled dataset: pairs of vehicle crops from
   `sentinel-solution/backend/data/crops/` (real saved crops from
   pipeline runs — check which ones came from real sandbox footage vs.
   the synthetic demo route by cross-referencing `VehicleEvent.camera_id`
   in `sentinel.db` against `cam01`-`cam05`, which are the synthetic
   demo's own cameras — anything else is real). You need both same
   -vehicle pairs (the same physical vehicle seen at two cameras — hard to
   get without ground truth; if the DB doesn't have enough real repeat
   sightings, note this as a limitation rather than fabricating pairs) and
   different-vehicle pairs (any two crops of different vehicles — easy,
   there are thousands).
2. Run `ColorHistogramEncoder().encode()` on each crop, compute pairwise
   cosine similarity (`analytics.reid.cosine_similarity`), and plot/report
   an ROC curve or at minimum a same-vs-different score histogram.
3. Pick a threshold off that curve (or state honestly that same-vehicle
   pairs couldn't be collected from available data, and recommend
   collecting them from a controlled test — e.g. one vehicle driven past
   2+ sandbox cameras deliberately).
4. Update the constant and its comment in `identity.py` to cite the actual
   analysis, not a guess. Update `HLD.md` if it references this number.

**Verification:** don't just claim the new number is better — re-run
`scripts/demo_end_to_end.py` (both plain and `SENTINEL_DEMO_PERSIST=1`
modes) to confirm the existing 5-camera evaluation scenario still passes
all its checks with the new threshold. If it doesn't, that's real
information about the tradeoff, not a bug to hide.

## Task 2 — A real held-out evaluation sample for ANPR (ML-4) — MATERIALLY ADVANCED 2026-09-05, still open

**Update, twice in one day — read both, the first update below was
superseded by the second:**

**First pass:** `scripts/real_anpr_scan.py` was run against all 30 real
sandbox cameras (20s each, no compositing): 466 real vehicle detections, 0
plate reads, with both the old heuristic localizer AND the new trained
`YoloPlateDetector`. Manual inspection of cam01/cam17 (wide-overview
cameras) suggested the plate was simply too small/far to read at those
angles.

**Second pass, same day, corrected the conclusion above:** following
direct hackathon-organizer guidance ("use any clearly-visible sandbox
camera for the demo"), reviewed saved crops from ALL 30 cameras, not just
the two initially inspected, and found `cam06` — a genuinely close-range,
front-facing camera (unlike cam01/cam17). Testing against it surfaced a
SECOND real bug, this time in `anpr.py`: the plate is a two-line format
(common on two/three-wheelers), and the OCR reader only ever
pattern-matched each detected line individually, so a legible two-line
plate could never match. **Fixed:** `read()` now joins multi-line
detections + applies bounded homoglyph correction
(`_ambiguous_variants`/`_best_pattern_match`). **Result:** 0/13 → 8/13 real
frames of the same vehicle now produce a pattern-valid read. See `HLD.md`
§3 for the full corrected writeup.

**What's still genuinely open, if picked up:** (1) this still isn't a
formal human-reviewed precision/recall table across a curated ground-truth
sample — it's real, measured evidence of capability, not a rigorous
accuracy number; (2) the 8 valid reads aren't character-consistent across
frames (`GJ05AAY6417` vs `GJ05AOY6417` vs `GJ05AQY6417`, etc.) —
`tracker.py`'s `consensus_plate()` does exact-string majority voting, so
these split votes land below the 0.5 confidence floor; a per-character
(position-weighted) consensus mechanism is the natural next step and
isn't built yet. If picked up, that's a self-contained, well-scoped task:
change `consensus_plate()` to vote per-character-position across a
track's accepted reads (weighted by each read's confidence), re-run
against `cam06`'s real saved frames, and confirm the result both
(a) recovers a single higher-confidence read and (b) doesn't regress the
existing single-line synthetic-plate path in `demo_end_to_end.py`.

## Task 3 — Minimal regression test suite (SWE-4) — DONE 2026-09-04

`sentinel-solution/backend/tests/` exists: 32 tests, all green, covering
exactly the `identity.py`/`tracker.py`/`geo.py` failure modes this task
originally asked for. Run with `python -m pytest tests -v` from `backend/`.
See `REVIEW_FINDINGS.md`'s SWE-4 entry for exactly what's covered. Nothing
to do here unless a future change to one of those three modules needs a
new test added to the existing suite.

## General rules for whoever picks this up

- Every fix needs a **real runtime verification**, not just "it imports"
  or "the diff looks right" — this project has repeatedly caught real
  bugs this way (see `REVIEW_FINDINGS.md` for several examples from
  today alone: a lock-ordering fix verified with real concurrent threads,
  a color-classification fix verified against synthetic images
  reproducing the exact named failure mode, etc.). Follow that pattern.
- If a fix reveals ANOTHER bug (this happened twice in today's session —
  fixing the geo-feasibility gate broke the demo script's own timing
  assumptions, which revealed the association window AND a missing clock
  -injection seam both needed fixing too), don't stop at the first green
  result — re-run the full integration path and look at what the UI
  actually renders from it.
- Never fabricate a result to look more complete — if real data isn't
  available (e.g. Task 2's same-vehicle pairs), say so explicitly rather
  than faking numbers.
- Update `HLD.md`/`REVIEW_FINDINGS.md` to reflect whatever you find,
  following the existing pattern of dated, specific entries (not vague
  "improved X" — cite what was measured/verified and how).
