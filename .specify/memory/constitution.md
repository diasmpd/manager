# Manager Constitution

Manager is a single-player football management game for Windows (personal use), with Football
Manager (SEGA) as the realism benchmark. A headless Python simulation core is driven by a Godot
desktop client.

## Core Principles

### I. Realism Is Measured, Not Assumed

- Every simulation system (match engine, quick sim, economy, transfers, player development)
  MUST declare quantitative calibration targets drawn from real football data (e.g. goals,
  shots, xG, possession, fouls and cards per match; wage/value distributions; ageing curves).
- A calibration harness MUST exist for each system and run over a large sample (≥1,000 matches
  or ≥10 simulated seasons). A change that moves a metric outside its tolerance band MUST NOT be
  merged unless the spec is amended to justify the new target.
- Football Manager is the reference for feature design. A feature that deviates from FM's
  approach MUST state why in its spec.
- Tactics MUST matter believably: no single tactic may dominate across opponents. Each spec that
  touches tactics MUST include an "exploit check" in its calibration.

Rationale: realism is the product. If it isn't measured it drifts silently.

### II. Deterministic, Reproducible Simulation

- All randomness MUST flow from an explicit, seedable RNG owned by the simulation context. Global
  random state, wall-clock time and dictionary ordering MUST NOT influence results.
- The same save, inputs and seed MUST produce the same match, season and world, bit for bit.
- Every match MUST be replayable from its seed plus the recorded user decisions (substitutions,
  tactical changes).

Rationale: reproducibility makes bugs debuggable, calibration trustworthy and replays (2D/3D)
possible.

### III. Headless Core, Thin Client

- The Python core MUST run fully without any UI: career, matches and world simulation are
  operable from tests and a CLI.
- The Godot client MUST talk to the core only through a versioned, documented local API contract
  (`contracts/`). The client MUST NOT contain game rules.
- The positional match engine MUST emit a time-sampled positional record (players and ball) so
  that text, 2D and future 3D views consume the same data without engine changes.

Rationale: the engine outlives any UI, and the planned 2D→3D path must not require rewrites.

### IV. Test-First for Game Logic

- Rules and simulation code MUST have tests written before or alongside the implementation, and
  the feature is not done until they pass.
- Probabilistic behaviour MUST be tested statistically with fixed seeds and explicit tolerance
  bands, not with single lucky runs.
- Every bug fix MUST add a regression test reproducing the bug from its seed.

Rationale: a simulation can look plausible while being wrong. Tests are the only safeguard.

### V. Smart Automation, Manager in Control

- Players MUST behave intelligently from their attributes and match state (e.g. a booked player
  eases off his tackles, a tired player conserves energy, players react to score and time). Each
  behaviour MUST carry a realistic trade-off, never a free bonus.
- Assistant actions (substitution or tactic suggestions) are suggestions by default. Automatic
  actions (e.g. auto-subs) MUST be opt-in per category and MUST be logged in the match report.
- Pain points the user reports from other games are first-class requirements and are tracked in
  the spec that addresses them.

Rationale: the game exists to remove tedious micromanagement without taking decisions away.

### VI. Data Rights and Separation

- Real-world club and player data MUST NOT be committed to the public repository. It lives in the
  private `manager-data` repository and is loaded through the import pipeline.
- The public repository MUST ship a fictional sample dataset that is sufficient to run all tests,
  calibration and the playable prototype.
- Imported data MUST record its provenance (source, date, transformation version) so that a
  re-import can be reproduced and audited.

Rationale: personal use of real data is fine; publishing it is not. Tests must never depend on
private data.

### VII. Incremental Delivery, Extension Points Kept Open

- Work is delivered in milestones (Prototype → v1 → later). Each spec MUST state which milestone
  it serves and MUST NOT build features of later milestones.
- Known future directions (3D view, online leagues with friends, more nations) MUST be kept
  possible through clean boundaries (save format, API contract, positional record). They MUST NOT
  be built speculatively.
- Prefer the simplest design that meets the current spec's calibration targets.

Rationale: an FM-scale game is huge. Shipping playable slices keeps it alive.

## Technical Constraints

- **Core**: Python ≥ 3.12, standard library plus vetted dependencies (each new dependency is
  justified in its plan). Type hints are required on public APIs.
- **Client**: Godot 4.x, Windows desktop as the primary target.
- **Persistence**: one SQLite database per career save. Schema changes ship with migrations.
- **Match simulation is two-tier**: a positional engine for matches the user's club plays or
  watches, and a fast statistical sim for background matches. Both MUST be calibrated to the same
  targets, and the quick sim MUST be validated against the positional engine.
- **Performance budgets** (reference: this Windows PC): positional match ≤ 10 s headless; a full
  world matchday via quick sim ≤ 5 s; advancing one in-game day without matches ≤ 1 s.
  Specs MAY tighten these.
- **Language**: in-game text is PT-BR. Code, comments, specs and docs are in English. User-facing
  strings MUST go through a localisation layer, not be hard-coded in logic.

## Development Workflow

- Every feature follows Spec Kit: `/speckit-specify` → (`/speckit-clarify`) → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement`. Specs live in `specs/NNN-feature-name/`.
- One branch per spec (`NNN-feature-name`), merged into `main` through a pull request that the
  owner reviews. Direct commits to `main` are limited to documentation fixes.
- A PR MUST have all tests passing and, if it touches a simulation system, MUST include the
  calibration report (before/after metrics) in its description.
- `docs/roadmap.md` tracks milestones and spec order and is updated when a spec merges.

## Governance

- This constitution supersedes other practices. Plans MUST include a Constitution Check, and any
  violation MUST be justified in the plan's Complexity Tracking table.
- Amendments are made via `/speckit-constitution`, with a version bump: MAJOR for removing or
  redefining a principle, MINOR for adding a principle or section, PATCH for wording.
- Every PR review verifies compliance with Principles I–VII.
- Runtime guidance for the coding agent lives in `CLAUDE.md`.

**Version**: 1.0.0 | **Ratified**: 2026-10-02 | **Last Amended**: 2026-10-02
