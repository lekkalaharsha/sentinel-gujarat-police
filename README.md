# Sentinel — Gujarat Police Innovation Challenge 2026

An interoperability layer over Gujarat's 26-department CCTV
infrastructure — camera registry + GIS (Model 1) plus direct unified
viewing/analytics (Model 2), with vehicle plate tracking, watchlist
alerting, and cross-camera identity resolution as the core demo.

For AI coding agents working in this repo: read `CLAUDE.md` first (it's
also the canonical instructions file for tools that read `AGENTS.md`).

## Where things live

- **`sentinel-solution/`** — the actual product: FastAPI backend +
  React/Vite frontend. Start with `sentinel-solution/README.md`.
  - `sentinel-solution/docs/` — Technical Proposal (`HLD.md`),
    `SCALABILITY.md`, code-review trackers
    (`REVIEW_FINDINGS.md`/`MODULE_GAP_ANALYSIS.md`), the architecture and
    workflow diagrams (`.drawio` + rendered `.png`), and archived research
    prompts (`promast/`).
- **`docs/hackathon/`** — challenge rules (`HACKATHON_DETAILS.md`), the
  deliverable-status matrix (`REQUIREMENTS_COVERAGE.md`), and the living
  task list (`TASKS.md`).
- **`docs/strategy/`** — the architecture decision record
  (`STRATEGY.md`), research prompts and findings
  (`RESEARCH_PROMPT.md`/`RESEARCH_EXISTING_SYSTEMS.md`), and
  `COMPETITIVE_TEARDOWN.md`.
- **`docs/submission/`** — organizer-facing material:
  `ORGANIZER_BRIEFING.md`, `EMAIL_DRAFT.md`, `DEMO_SCRIPT_OWN_FEED.md`.
- **`docs/assets/`** — the presentation deck (`.pptx`/`.pdf`) and
  supporting screenshots; `docs/assets/archive/` holds superseded
  versions kept for history only.
- **`deck-build/`** — the script that generates the presentation deck
  from this repo's own docs (`docs/assets/Sentinel_Solution_Presentation.pptx`).

## Deadline

Phase 1 submission: **15 September 2026**. Event/Grand Finale: 22–23 Sep
2026. See `docs/hackathon/TASKS.md` for current status.
