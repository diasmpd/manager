---
description: "Task list for 006 Tactics"
---

# Tasks: Tactics

**Tests**: REQUIRED (Constitution IV). Write the tests first and see them fail.

## Phase 1: Setup

- [x] T001 Create `core/src/manager_core/tactics/` and `reference/tactics/`, and add `reference/tactics/*.toml` to the package data.

## Phase 2: Foundational

- [x] T002 [P] Write `reference/tactics/options.toml`, the full FM26 set from the spec:
  - the 7 mentality levels;
  - the team instructions by phase, each with its settings and default;
  - the 14 player instructions with settings;
  - the set-piece options.
- [x] T003 [P] Add the OOP formations to `reference/formations.csv` (4-1-4-1, 4-5-1, 4-4-1-1, 5-4-1, 4-1-2-3, 3-4-3, 5-2-3, 4-3-1-2 and others), plus a table of OOP suggestions per IP formation (3 each). 001's formation tests stay green.
- [x] T004 [P] Write `reference/tactics/roles.toml` with all IP and OOP roles of the spec. For each: phase, valid positions, key attributes with weights, locked player instructions, and lever modifiers.
- [x] T005 Tests then `tactics/model.py` and `catalogue.py`:
  - `Tactic` and its default;
  - validation with codes T001 (unknown option or setting), T002 (role invalid for slot), T003 (instruction locked by role), T004 (invalid set-piece taker) and T005 (unknown formation);
  - OOP suggestions;
  - role suitability.

## Phase 3: US2 - Effects in the quick sim (P2, built before US1's UI because the UI needs it)

- [x] T006 [P] Write `reference/tactics/effects.toml`: option → setting → lever multipliers, plus the interaction rules (research R2, R3). Every option has a cost lever.
- [x] T007 Tests then `tactics/effects.py`: `levers(own, opponent, flank_balance)` (game state, minute and score, comes in with T008/T010 when needed). Neutral against neutral gives all 1.0. Each documented direction holds per option in a statistical engine test, with fixed seeds and bands.
- [x] T008 Engine: apply levers (shot rate and quality, allowed, possession, fouls and cards, fatigue after minute 60, set pieces, counter chances, error chances) and role scaling in the ratings. The quick sim reads both sides' tactics. Reports record tactic summaries.

## Phase 4: US4 - AI styles (P4, needed before calibration)

- [x] T009 [P] Write `reference/tactics/styles.toml`: 6 styles as full tactics, squad-trait rules and adaptation rules.
- [x] T010 Tests then `tactics/ai.py`:
  - at least 3 distinct styles among the sample's 12 clubs;
  - assignment is deterministic;
  - a big underdog away is at most Cautious and mid block;
  - in-match steps after minute 70.

## Phase 5: US3 - Calibration with styles, and the exploit check (P3)

- [x] T011 Harness: AI styles for every club in both samples. Refit `model.toml` so both gates pass.
- [x] T012 Tests then `calibration/exploit.py`: a mirrored-strength grid (styles plus single-option variations against the 6 styles), a points-per-match matrix, and the gate (max gain ≤ 0.20 points per match; no tactic best against every style). Add it to the PR gate report and CLI. Retune the effects until it passes.

## Phase 6: US1 - The user's tactic (P1)

- [x] T013 Tests then the career tactic:
  - a default tactic is derived from the selection's formation;
  - the facade: `tactic_options`, `suggest_oop_formations`, `role_suitability`, `validate_tactic`, `confirm_tactic`;
  - save format v3 with a migration from v2;
  - the user's matches use the tactic.
- [x] T014 TUI Tactics screen: formations with OOP suggestions, mentality, instructions by phase, roles per slot with suitability, player instructions with locked ones marked, and set-piece takers. Pilot tests.

## Phase 7: Polish

- [x] T015 Docs (README, roadmap, quickstart), full suites, both gates, ruff and mypy, then the PR.
