# Sentinel — Gujarat Police Innovation Challenge 2026

Read `HACKATHON_DETAILS.md` and `STRATEGY.md` in this directory before doing
anything else in a new session — they are the source of truth for the
challenge rules and our architecture decisions. Do not re-derive either
from memory; re-read the files, they may have been updated.

## What this project is

A submission for Gujarat Police's Sentinel hackathon: an interoperability
layer over Gujarat's 26-department CCTV infrastructure — camera registry +
GIS (Model 1, mandatory) + direct unified viewing/analytics (Model 2), with
vehicle plate tracking, watchlist alerting, and cross-camera identity
resolution as the core demo.

**Deadline: 7 September 2026** (Phase 1 submission). Event: 10–11 Sep 2026.
Treat remaining time as scarce — see "Scope discipline" below.

## Directory map

- `HACKATHON_DETAILS.md` — full rules, prize structure, evaluation
  criteria, submission requirements, and the sandbox integration spec
  (real endpoints: `cctv.corp8.cloud` for HLS/catalogue,
  `103.250.160.189` for RTSP/WHEP — §13a is authoritative over generic
  `<host>` examples elsewhere in the file).
- `STRATEGY.md` — the architecture decision record, synthesized from two
  independent research passes (ChatGPT + DeepSeek). Read this before
  proposing any architecture change. Do not silently deviate from its
  IN/OUT lists without flagging the change to the user first.
- `RESEARCH_PROMPT.md` — the prompt used to get that research; reusable if
  more research is needed later.
- `sentinel-solution/` — the actual backend (FastAPI). See its own
  `README.md` for the module map and what's stubbed vs. real.

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

## Coding rules specific to this project

- **Every "real" implementation ships with a pluggable stub.** Pattern:
  `Protocol` interface + a stub that's honest about doing nothing (not a
  fake success) + a real implementation with a documented gap if one
  exists (e.g. `StubMakeModelClassifier` explicitly says no good
  open-source Indian vehicle make/model classifier exists — don't fabricate
  a result to look more complete).
- **Never claim a capability that isn't wired in.** If a detector/OCR/
  encoder is stubbed, the docs and code comments must say so. This is a
  government/police jury evaluation — false claims are a bigger risk than
  visible gaps.
- **Verify runtime behavior, not just `ast.parse`.** This codebase has
  caught real bugs (a `.get()` call on a list, a `None`-embedding crash)
  that syntax checks alone missed. Every new pipeline path should get an
  actual run — synthetic data is fine, but exercise the real code path
  end-to-end, including the failure mode it's meant to handle (e.g. "what
  if the plate misreads" tested with a scripted bad OCR read, not assumed).
- **Sandbox credentials are secrets.** Never `cat`/echo the session cookie
  file or access password into a tool result or transcript. Use it via
  `-b`/`--cookie-jar` flags, env vars, or `.env` (gitignored) — not printed.
- **Timing rules for anything touching the camera grid** (see
  `HACKATHON_DETAILS.md` §13a): force RTSP over TCP, derive all timing from
  PTS never `CAP_PROP_FPS`/wall-clock, reconnect with backoff not a tight
  loop, treat scene-loop discontinuities as expected and reset dependent
  state, never assume a uniform frame rate or camera grid.

## Git rules

This directory is **not yet a git repository**. Before any git operations:
1. Confirm with the user whether/when to `git init` — don't do it silently
   as a side effect of an unrelated task.
2. Once initialized: commit in logical units (e.g. "add temporal plate
   fusion", not one giant commit), never `--amend` published commits, never
   force-push, never commit `.env` or any file containing the sandbox
   access password/session cookie.
3. Only commit when the user explicitly asks — per standing harness rules,
   don't commit proactively even at a natural checkpoint.

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
