# Sentinel — Gujarat Police Innovation Challenge 2026

Read `docs/hackathon/HACKATHON_DETAILS.md` and `docs/strategy/STRATEGY.md`
before doing anything else in a new session — they are the source of
truth for the challenge rules and our architecture decisions. Do not
re-derive either from memory; re-read the files, they may have been
updated.

This is the single instructions file for this repo — for any AI coding
agent, not just Claude Code. If your tool only reads `AGENTS.md`, that
file is a one-line pointer back to this one; there is no separate,
possibly-drifted copy to fall out of sync.

## What this project is

A submission for Gujarat Police's Sentinel hackathon: an interoperability
layer over Gujarat's 26-department CCTV infrastructure — camera registry +
GIS (Model 1, mandatory) + direct unified viewing/analytics (Model 2), with
vehicle plate tracking, watchlist alerting, and cross-camera identity
resolution as the core demo.

**Deadline: 15 September 2026** (Phase 1 submission, updated 2026-09-05 —
was originally 7 Sep, confirmed moved via the live sentinel.gujarat.gov.in
schedule page). Event/Grand Finale: 22–23 Sep 2026 (was 10–11 Sep).
Treat remaining time as scarce — see "Scope discipline" below.

## Directory map

- `docs/hackathon/HACKATHON_DETAILS.md` — full rules, prize structure,
  evaluation criteria, submission requirements, and the sandbox
  integration spec (real endpoints: `cctv.corp8.cloud` for HLS/catalogue,
  `103.250.160.189` for RTSP/WHEP — §13a is authoritative over generic
  `<host>` examples elsewhere in the file).
- `docs/hackathon/` — also holds `REQUIREMENTS_COVERAGE.md` (deliverable
  -status matrix) and `TASKS.md` (living task list).
- `docs/strategy/STRATEGY.md` — the architecture decision record,
  synthesized from two independent research passes (ChatGPT + DeepSeek).
  Read this before proposing any architecture change. Do not silently
  deviate from its IN/OUT lists without flagging the change to the user
  first.
- `docs/strategy/` — also holds `RESEARCH_PROMPT.md` (reusable prompt for
  further research), `RESEARCH_EXISTING_SYSTEMS.md`, and
  `COMPETITIVE_TEARDOWN.md`.
- `docs/submission/` — organizer-facing material: `ORGANIZER_BRIEFING.md`,
  `EMAIL_DRAFT.md`, `DEMO_SCRIPT_OWN_FEED.md`.
- `docs/assets/` — the presentation deck (`.pptx`/`.pdf`), screenshots,
  and other submission images. `docs/assets/archive/` holds superseded
  versions kept for history, not current deliverables.
- `sentinel-solution/` — the actual backend (FastAPI) and frontend
  (React/Vite). See its own `README.md` for the module map and what's
  stubbed vs. real, and `sentinel-solution/docs/` for the Technical
  Proposal (`HLD.md`), `SCALABILITY.md`, and the code-review trackers.

## Scope discipline (the main risk to manage)

This project has already had scope pulled in multiple directions by
external research (VISWAS/TRINETRA reframing, re-ID, ByteTrack, MediaMTX,
governance/audit features). **Every one of those was deliberately filtered
down to what's achievable in the time budget** — see STRATEGY.md's
"What's IN" / "What's OUT" lists. When new ideas come up (from the user, from
further research, or from your own judgment):

1. Check whether it's already explicitly deferred in STRATEGY.md's OUT list
   (face recognition, fingerprint integration, full 80k ingestion, new VMS,
   actually deploying Kafka/MediaMTX this week). If so, say so before
   building it — don't silently implement deferred scope.
2. Prefer extending existing seams (pluggable stub interfaces) over adding
   new architectural layers.
3. If a change would alter the STRATEGY.md decision itself, update that
   file as part of the change — don't let code and strategy doc drift apart.
4. Prefer the smallest complete change that satisfies the request. Avoid
   unrelated refactoring, renaming, formatting, or dependency upgrades,
   and avoid uncontrolled retries or unnecessary new infrastructure (e.g.
   a message queue or cache layer) — those are explicitly deferred to
   later scale tiers in `SCALABILITY.md`, not this pilot.

## Stack and tooling (what this repo actually uses)

This is a solo/small-team hackathon submission, not a multi-track
monorepo — there is **no Docker/docker-compose, no Alembic, no `uv`, no
TypeScript, and no CI configured.** Don't introduce any of these without
an explicit requirement — that's scope creep per the section above, not
just a tooling nit.

- **Backend**: Python 3.11, FastAPI, Pydantic, SQLAlchemy 2.x. Plain
  `pip` + a checked-in `.venv` (`sentinel-solution/backend/.venv`) via
  `requirements.txt`/`requirements-ml.txt` — no `uv`, no `pyproject.toml`.
- **Database**: SQLite (`sentinel.db`; `DATABASE_URL` is env-overridable
  toward PostgreSQL at larger scale per `SCALABILITY.md`, but SQLite is
  what's actually run today). **No Alembic** — schema changes are
  hand-rolled additive migrations in
  `sentinel-solution/backend/app/db/session.py`'s `_ADDITIVE_MIGRATIONS`
  list, checked at startup by `_check_models_match_db()`. Table names are
  singular `snake_case` (`vehicle_identity`, `camera_registry`, `alert`),
  not plural — match this, don't pluralize new tables.
- **Frontend**: React 19 + Vite, plain JavaScript/JSX (not TypeScript).
  Lint via `oxlint` (`.oxlintrc.json`), not ESLint. No Prettier config
  exists — don't add one silently.
- No linter is configured for backend Python (no Ruff/flake8 config
  present) — match surrounding code style; don't invent a linter config
  unprompted.
- Follow the existing repository structure and established patterns
  (route-per-file in `app/api/routes_*.py`, one `APIRouter` per resource
  with a flat, **non-versioned** prefix — `/cameras`, `/vehicle`, `/live`,
  `/admin`, `/auth`, `/alerts`, `/watchlist`, not `/api/v1/...` — match
  this, don't introduce API versioning unilaterally).
- Read `sentinel-solution/README.md`, `sentinel-solution/docs/HLD.md`, and
  `docs/strategy/STRATEGY.md` before making significant changes — there is
  no separate `CONTRIBUTING.md`.

## Build and test commands

```bash
# Backend tests (from sentinel-solution/backend, using the checked-in venv)
cd sentinel-solution/backend
.venv/Scripts/python.exe -m pytest tests -v      # Windows
# .venv/bin/python -m pytest tests -v            # POSIX

# Run the backend (requires sandbox env vars from sentinel-solution/.env —
# see "Sandbox credentials are secrets" below; config.py has no dotenv
# autoload, so export them into the shell first, e.g. by parsing .env)
cd sentinel-solution/backend
.venv/Scripts/python.exe -m app.main

# Frontend lint
cd sentinel-solution/frontend && npm run lint      # oxlint
# No `npm run format` script exists — don't assume Prettier is configured.

# Frontend dev server / build
cd sentinel-solution/frontend && npm run dev
cd sentinel-solution/frontend && npm run build

# No pre-commit config, no Docker/Compose in this repo — skip those
# steps entirely rather than assuming they exist.
```

Never claim a test, build, migration, lint, or command passed unless it
was actually run successfully — this repo has caught real runtime bugs
(a `.get()` on a list, a `None`-embedding crash, an unproxied HLS
encryption-key URL) that a syntax check alone missed. If a check cannot
be run, report that clearly.

## Coding rules specific to this project

- **Every "real" implementation ships with a pluggable stub.** Pattern:
  `Protocol` interface + a stub that's honest about doing nothing (not a
  fake success) + a real implementation with a documented gap if one
  exists (e.g. `StubMakeModelClassifier` explicitly says no good
  open-source Indian vehicle make/model classifier exists — don't fabricate
  a result to look more complete). This is already used for every ML
  component (`analytics/detector.py`, `analytics/anpr.py`,
  `analytics/plate_detector.py`) — extend that pattern for new analytics
  code, don't invent a parallel one.
- **Never claim a capability that isn't wired in.** If a detector/OCR/
  encoder is stubbed, the docs and code comments must say so. This is a
  government/police jury evaluation — false claims are a bigger risk than
  visible gaps. Do not disable failing tests, hide errors, or fabricate
  test/model results to make something look more complete.
- **Verify runtime behavior, not just `ast.parse`.** This codebase has
  caught real bugs (a `.get()` call on a list, a `None`-embedding crash)
  that syntax checks alone missed. Every new pipeline path should get an
  actual run — synthetic data is fine, but exercise the real code path
  end-to-end, including the failure mode it's meant to handle (e.g. "what
  if the plate misreads" tested with a scripted bad OCR read, not assumed).
- **Sandbox credentials are secrets.** Never `cat`/echo the session cookie
  file or access password into a tool result or transcript. Use it via
  `-b`/`--cookie-jar` flags, env vars, or `.env` (gitignored) — not printed.
  This applies to any credential in this repo, not just the sandbox
  password — e.g. the bootstrap admin API key
  (`auth.py::ensure_default_admin_key`) is `print()`-ed directly,
  deliberately bypassing the logging framework so it never lands in a
  persistent log; follow that precedent for any future one-shot secret
  reveal, and never paste a minted key into a committed file.
- **Timing rules for anything touching the camera grid** (see
  `docs/hackathon/HACKATHON_DETAILS.md` §13a): force RTSP over TCP, derive all timing from
  PTS never `CAP_PROP_FPS`/wall-clock, reconnect with backoff not a tight
  loop, treat scene-loop discontinuities as expected and reset dependent
  state, never assume a uniform frame rate or camera grid.
- **Treat all external/AI-derived input as untrusted** — API input,
  uploads, filenames, external CDN responses, and ANPR/OCR output all need
  validation before they reach identity resolution or an alert (e.g.
  `anpr.py`'s `PLATE_PATTERN` regex must reject non-plate-format OCR
  output before it can spawn a false identity or false watchlist alert —
  don't remove or weaken that gate).
- **Never expose raw camera credentials.** `rtsp_url`/`whep_url` embed
  real sandbox `email:password@` credentials and must stay admin-only
  (`routes_cameras.py::_merged_camera_view` already enforces this) — the
  frontend only ever touches `hls_url` via the authenticated proxy.
  Preserve this boundary in any new camera-data endpoint.
- **Enforce authorization at the resource/object level, not just role.**
  E.g. `/admin/audit-log` is scoped to the caller's own `user_id` unless
  admin, not just gated by role — match this pattern for new admin-ish
  endpoints rather than a flat role check.
- **Database schema changes go through the additive-migration system**,
  not manual `ALTER TABLE`: add/modify the model in `app/db/models.py`,
  then add a matching entry to `_ADDITIVE_MIGRATIONS` in
  `app/db/session.py`. Never drop/recreate `sentinel.db` to "fix" a
  migration — it holds real accumulated demo data (onboarded cameras,
  identities, alerts) from earlier sessions; treat it like any other
  uncommitted work worth preserving.
- **Naming**: Python `snake_case`/`PascalCase` classes/`UPPER_SNAKE_CASE`
  constants (see `app/config.py` for the env-var-backed constant style);
  JS `camelCase`/React components `PascalCase`. Avoid wildcard imports,
  dead code, commented-out implementations, and vague TODOs.


## Git rules

**Changed 2026-09-10: this repo now uses a full branch+PR workflow**,
even though there is still one contributor and no CI/second reviewer —
the user explicitly opted into this over staying with the prior direct-
to-`master` practice. Repo: `github.com/lekkalaharsha/sentinel-gujarat-
police`. There is still no issue tracker (GitHub Issues aren't in use) —
don't invent one; branches/PRs are scoped directly off the task at hand
or `docs/hackathon/TASKS.md`, not an issue number.

- Follow: `branch -> implementation -> tests -> PR -> self-review -> merge`.
- **Only commit, branch, push, open/merge a PR, tag, or create a release
  when the user explicitly asks** — per standing harness rules, don't do
  any of these proactively even at a natural checkpoint, and a prior
  approval doesn't carry forward to a new unrelated change.
- **Branch naming**: `feature/<short-description>`, `fix/<short-description>`,
  `docs/<short-description>` (no issue number prefix, since there's no
  issue tracker) — e.g. `feature/model1-gis-layer-toggle`,
  `fix/create-api-key-400-status`.
- Commit in logical units (e.g. "backend fixes" separate from "frontend
  rebuild" separate from "docs restructure") rather than one giant
  commit — see the `v0.1.0` history for the pattern this project has
  actually used.
- **PRs**: use `gh pr create`. The description states what changed, why,
  how it was tested, and any API/database/integration impact (see the
  template in this file's top-level "Creating pull requests" instructions).
  Since there's no second reviewer, the self-review step is not optional —
  read the complete diff before calling a PR ready, per the completion
  checklist below.
- Merge via `gh pr merge` only when the user asks; don't auto-merge on
  green (there is no CI configured to be green against).
- Never `--amend` a published/already-pushed commit; never force-push.
  Never force-push or delete a branch containing unmerged work without
  confirming with the user first.
- Never commit `.env`, `sentinel.db`, model weights (`*.pt`/`*.onnx`),
  `sentinel-solution/demo_output/`, a minted API key, or any other
  secret/generated-junk file — check `git status` after a broad `git add`
  before committing, not just before.
- **No pre-commit hooks are configured in this repo** — don't invent one
  unprompted, and there is nothing to bypass with `--no-verify`.
- **Tags and releases**: this project versions milestones with annotated
  tags (`v0.0.1` baseline, `v0.1.0` first feature+restructure release)
  plus a matching `gh release create` with real, specific release notes
  (what changed since the last tag, not a generic template) — continue
  this pattern for future milestones rather than starting a new scheme,
  cut from `master` after a PR has merged, and only cut a tag/release
  when the user asks for one.


## Testing and completion checklist

Before declaring a task complete:

- [ ] Requirement is satisfied and existing architecture/conventions were
      followed (stub/real pattern, additive-migration pattern,
      resource-prefixed non-versioned API routes).
- [ ] Naming/database/API conventions above were followed for new code.
- [ ] Input validation and security implications were considered.
- [ ] A matching `_ADDITIVE_MIGRATIONS` entry was added if the schema
      changed.
- [ ] Relevant `backend/tests/` were added/updated and **actually run**
      (`python -m pytest tests -v`), not assumed to pass.
- [ ] `npm run lint` (oxlint) was run for frontend changes.
- [ ] The actual runtime behavior was exercised end-to-end (a real HTTP
      call, a real script run, a real browser check) — not just a syntax
      or type check. See the `verify` skill.
- [ ] No secrets, debug code, or unrelated changes were introduced.
- [ ] API and cross-component compatibility were considered (frontend
      `api.js` callers, in particular — treat existing response field
      names as a contract; don't silently rename one).
- [ ] Documentation was updated when setup, configuration, API, or
      behavior changed (`sentinel-solution/README.md`,
      `sentinel-solution/docs/HLD.md`, `docs/hackathon/TASKS.md` as
      relevant).
- [ ] The complete diff was self-reviewed.

When finishing, briefly report what changed, tests actually run,
API/database/config changes, integration impact, and anything still
requiring human review — matching the honesty-over-completeness bar this
project holds itself to throughout `sentinel-solution/docs/REVIEW_FINDINGS.md`
and `sentinel-solution/docs/MODULE_GAP_ANALYSIS.md`.

## Skills / agents / MCP usage for this project

- No project-specific skills or MCP servers are configured here. Use the
  globally available skills (`verify`, `code-review`, etc.) at their
  normal trigger points — e.g. run `verify` after a nontrivial pipeline
  change before declaring it done, rather than trusting a syntax check.
- Don't spawn subagents for this project's core implementation work unless
  a task is genuinely independent and context-heavy (e.g. "go read all of
  ChatGPT's/DeepSeek's cited sources and summarize" would be fork-worthy;
  "implement the next pipeline stage" is not — do it inline, the user is
  actively steering architecture decisions turn-by-turn and needs that
  context preserved, not delegated).
- The global `~/CLAUDE.md` graphify rule doesn't apply here — this project
  has no `graphify-out/` graph.

## Working style this user has established

- Wants concrete artifacts (files written, code run) over descriptions of
  what could be built.
- Reacts to and directs architecture based on external research (ChatGPT/
  DeepSeek) — expect to synthesize incoming research against STRATEGY.md
  rather than either blindly adopting it or ignoring it.
- Prefers decisions get captured in a durable file (STRATEGY.md pattern)
  over staying only in conversation.
- Time pressure is real (hackathon deadline) — bias toward finishing a
  working vertical slice over broad partial coverage.
