# Implementation Plan: Positional Match Engine

**Branch**: `008-positional-engine` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

## Summary

The user club's matches are played by a positional engine. 22 players and the ball move on a real
pitch at 4 Hz, and each player decides from his attributes, the 006 tactic, his roles and
instructions, and the match state (see [research.md](research.md)).
- **Output**: the same `MatchReport` as the quick sim, plus a 2 Hz positional record for the 2D
  view in 008b.
- **Live play**: the match is a stepper (`LiveMatch`). The clients drive the clock through new
  contract methods, so the owner can pause at any time to substitute or change the tactic. Every
  decision is recorded, and a match replays exactly from its seed plus the decisions.
- **Calibration**: the engine uses the same targets, with its own PR and milestone samples, and
  is cross-validated against the quick sim.
- **The quick sim's 3-goal shortfall** is fixed with a mechanism first seen in the engine: after
  a two-goal lead, the leading side relaxes and the trailing side still pushes.

## Technical Context

- **Language**: Python ≥ 3.12, standard library only. The engine is pure Python (R1: 1–2 s a
  match, measured on the movement core). The clients are GDScript (Godot 4.7) and Textual (TUI).
- **Storage**: SQLite save format **v4**, with a `records` table holding zlib-compressed int16
  samples per user match, and a v3 → v4 migration.
- **Data**: `reference/positional/model.toml` holds every engine parameter: speeds, decision
  weights, xG coefficients, energy and game-state intents.
- **Testing**:
  - unit tests of geometry, movement and decisions;
  - paired-seed behaviour tests (FR-007);
  - determinism, and replay with decisions;
  - live-match contract tests;
  - positional PR and milestone gates, and cross-validation;
  - the quick sim's gates after the 3-goal fix;
  - the Godot and TUI pause tests.
- **Performance**: 1–2 s per match (budget 10 s); a season with live user matches in under
  2 minutes.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Realism measured | ✅ | The same targets for both tiers; positional gates; cross-validation; the 3-goal fix with unchanged targets. |
| II. Determinism | ✅ | A seeded engine with a fixed step order; decisions stamped with match time; a replay test (SC-005). |
| III. Thin clients and the positional record | ✅ | The record is emitted (FR-004). Pause and changes go through the contract (1.2), and all rules stay in the core. |
| IV. Test-first | ✅ | Behaviour tests and gates are written before or with the engine. |
| V. Manager in control | ✅ | Pause at any time; the assistant substitutes only when the owner doesn't. |
| VI. Data rights | ✅ | No data changes. |
| VII. Incremental | ✅ | Text view only (2D is 008b), no injuries and no weather. |
| Budgets | ✅ | 10 s per positional match: targeting 1–2 s. |

## Project Structure

```text
core/src/manager_core/
├── positional/
│   ├── pitch.py       # dimensions, geometry, zones, the xG model
│   ├── state.py       # players (position, velocity, energy, cards), the ball, team intents
│   ├── shape.py       # tactical targets: formation slot × phase × ball × instructions × role
│   ├── decide.py      # on-ball options and choice; pressing, marking, duels, fouls, keepers
│   ├── engine.py      # LiveMatch: step(), apply(decision), events, report, record
│   ├── record.py      # 2 Hz sampling, compact encoding (zlib int16)
│   └── params.py      # loads reference/positional/model.toml
├── reference/positional/model.toml
├── quicksim/provider.py    # precomputed result slot; positional play for the user club
├── quicksim/engine.py, reference/quicksim/model.toml   # the 3-goal mechanism (R5)
├── calibration/            # positional samples and gates, cross-validation
├── career/store.py         # save format v4: records table
├── api.py, server/methods.py   # live match: match.start/advance/substitute/tactic/state/finish
client/scenes/screens/match_day.gd   # drives the clock; pause; substitutions and tactics panels
tui/src/manager_tui/app.py           # the same in the terminal
tools/tune_positional.py
```

## Phases

1. **Engine skeleton**:
   - the pitch, state and movement;
   - the shape;
   - possession and passing;
   - shots and xG;
   - goals and restarts;
   - the report and the record;
   - determinism.
2. **The football**:
   - duels, fouls and cards (with the spec 003 caution);
   - keepers;
   - set pieces;
   - energy;
   - substitutions;
   - game-state intents;
   - every 006 option's positional meaning;
   - the behaviour tests.
3. **Calibration**:
   - the positional tuner;
   - the PR and milestone gates;
   - cross-validation;
   - the 3-goal mechanism found in the engine and ported to the quick sim, with both quick-sim
     gates passing.
4. **Career and live play**:
   - the provider's precomputed slot;
   - `LiveMatch` in the facade and the contract (1.2);
   - save v4 with records;
   - closing mid-match resumes before the match day.
5. **Clients**: the Godot match day with pause and the substitution and tactics panels, the same
   in the TUI, and their tests.
6. **Polish**: docs, both suites, all gates, then the PR.

## Complexity Tracking

| Item | Why it is needed | Simpler alternative rejected |
|---|---|---|
| A second engine with its own calibration | The constitution's two-tier design, and the positional record | Extending the quick sim cannot produce positions |
| A live-match protocol | The owner's decision: pause at any time | Pre-match only (the owner chose otherwise) |
