---
description: "Task list for 003 Quick Sim"
---

# Tasks: Quick Sim

**Input**: Design documents from `specs/003-quick-sim/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: REQUIRED (Constitution IV). Write the tests first and see them fail.

**Paths**: the package is `core/src/manager_core/`; tests are in `core/tests/`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Create the packages `core/src/manager_core/quicksim/__init__.py` and `core/src/manager_core/calibration/__init__.py`, and the reference folders `reference/quicksim/` and `reference/calibration/` (each with `__init__.py`). Add `reference/quicksim/*.toml` and `reference/calibration/*.toml` to the package data in `core/pyproject.toml`.
- [X] T002 [P] Create `core/tools/` (dev-only, not packaged) and `core/calibration/` (committed reports).

---

## Phase 2: Foundational (blocks all stories)

### Tests first

- [X] T003 [P] Unit tests `core/tests/unit/test_quicksim_params.py`:
  - the bundled `model.toml` loads and has a stable `params_hash` (it changes when any value changes);
  - a missing key or a rate outside (0, 1) raises `ModelParamsError` with code `Q001` and the key path;
  - ranges must be ordered.
- [X] T004 [P] Unit tests `core/tests/unit/test_quicksim_report.py` for `Minute`, `MatchEvent`, `SideStats`, `MatchReport` and `check_invariants(report, result)`. Hand-built reports that violate each invariant in data-model.md are rejected, with one test per invariant:
  - goals > shots on target;
  - possession ≠ 100;
  - an event by a player not on the pitch;
  - a third yellow;
  - an event after a red;
  - card totals ≠ per-player cards;
  - more than 5 substitutions;
  - a returning player.

  Also: `Minute(90, 4)` formats as "90+4", and minutes order by (base, added).
- [X] T005 [P] Unit tests `core/tests/unit/test_quicksim_ratings.py`:
  - composites are on the 1–20 scale;
  - raising a forward's finishing raises attack and not defence;
  - raising a centre-back's tackling raises defence;
  - removing a player (red card) lowers each composite he contributed to;
  - a GK-less XI gets a low goalkeeping rating;
  - the result is deterministic and independent of player order.
- [X] T006 [P] Contract test `core/tests/contract/test_calibration_targets.py`:
  - the bundled `quicksim-targets.toml` loads with every metric id from contracts/calibration-targets.md, each with a source and a retrieved date;
  - the values match the spec's table (goals 2.50 in 2.30–2.70; H/D/A 48.6/26.1/25.3 ±4 pp; yellows 5.2 in 4.5–6.0; reds 0.25 in 0.17–0.33; Mineiro draw 29% in 22–36%);
  - an unknown id, or `target` outside `low..high`, is rejected with code `C001` and the key path.

### Implementation

- [X] T007 [P] Implement `core/src/manager_core/quicksim/params.py`: `ModelParams` (frozen), `load_params()` and `load_params_file(path)`, `ModelParamsError` (Q001), and `params_hash` (SHA-256 of the canonical serialisation).
- [X] T008 [P] Write `core/src/manager_core/reference/quicksim/model.toml` with the initial values from research R3–R8 and R11. Every group gets a comment naming the research entry. `model_version = "0.1"`.
- [X] T009 [P] Implement `core/src/manager_core/quicksim/report.py`: `Minute`, `MatchEvent` (kinds `goal`, `own_goal`, `penalty_goal`, `penalty_miss`, `yellow`, `second_yellow`, `red`, `sub`), `SideStats`, `MatchReport` and `check_invariants`.
- [X] T010 [P] Implement `core/src/manager_core/quicksim/ratings.py`: `TeamRatings` and `rate(on_pitch, formation, dataset)`, per research R2 (weights table; contributions scaled by `suitability`; divided by a full XI's weight).
- [X] T011 [P] Implement `core/src/manager_core/calibration/targets.py` (loader, C001) and write `core/src/manager_core/reference/calibration/quicksim-targets.toml` with every row of the spec's calibration table: sources verbatim, `retrieved = 2026-10-02`.
- [X] T012 Extend 002 in `core/src/manager_core/competition/results.py` and `competition/season.py`:
  - `Result.report: MatchReport | None = None` (type imported under TYPE_CHECKING to keep `competition` independent);
  - `MatchContext.neutral: bool = False`, set by `Season` for `venue = "neutral"` stages;
  - `ResultProvider.shootout(..., *, last_result: Result | None = None)`, with `Season` passing the last leg's result;
  - `PlaceholderProvider` accepts and ignores `last_result`.

  Run the 002 suite: it must stay green.
- [X] T013 Add the 003 strings to `core/src/manager_core/i18n/pt_BR.py`:
  - stat labels (Finalizações, No alvo, xG, Posse, Escanteios, Faltas, Amarelos, Vermelhos);
  - event texts (gol, gol contra, pênalti, pênalti perdido, amarelo, segundo amarelo, vermelho, substituição);
  - "Ainda não disputado";
  - calibration labels and verdicts (OK / FORA / AVISO), one description per metric id;
  - the Q001/C001 messages.

**Checkpoint**: parameters, ratings, the report model and the targets load and pass their tests;
002 is still green.

---

## Phase 3: User Story 1 - Believable results for every match (P1) 🎯 MVP

**Goal**: the quick sim plays every match of a season, deterministically, with calibrated
scorelines.

**Independent Test**: play seasons with the quick sim; the PR gate's primary scoreline targets
pass.

### Tests (first)

- [X] T014 [P] [US1] Unit tests `core/tests/unit/test_quicksim_squad.py`:
  - `MatchSquad` picks 001's best XI for 4-4-2 and a bench of ≤ 9 that includes a second goalkeeper when the squad has one;
  - the XI and bench are cached per club (a second call costs no assignment);
  - a squad of 10 players still produces an XI (an outfield player in goal), with a flag set.
- [X] T015 [P] [US1] Unit tests `core/tests/unit/test_quicksim_engine.py`:
  - `simulate_match` is deterministic for the same RNG seed;
  - results differ across seeds;
  - `check_invariants` holds on 2,000 matches between random sample clubs (SC-005);
  - with `neutral=True`, home and away goal means over 2,000 mirrored matches are within noise of each other;
  - a much stronger side wins more often than it loses.
- [X] T016 [P] [US1] Integration test `core/tests/integration/test_quicksim_season.py`:
  - `start_season` now defaults to the quick sim (`source == "quick_sim"`, every result has a report);
  - 200 Mineiro seasons complete with 002's invariants (the 1,000-season version is `slow`);
  - a match replayed alone (same season seed and match id) equals the in-season result (SC-003);
  - no table row is `decided_by == "draw"` because cards were missing (SC-007: card totals are present on every result).
- [X] T017 [P] [US1] Update 002's tests that assert placeholder behaviour (`test_placeholder.py`, `test_season_play.py`, CLI "(provisório)" checks) to pass `result_provider=PlaceholderProvider(dataset)` explicitly, or to expect no "(provisório)" mark with the quick sim.
- [X] T018 [P] [US1] Performance test `core/tests/integration/test_quicksim_performance.py` (`slow`, limit from `MANAGER_PERF_LIMIT_S`):
  - a Mineiro matchday takes < 0.5 s once lineups are cached;
  - a full season takes < 3 s from a cold provider;
  - a 10-match league matchday takes < 1 s.

### Implementation

- [X] T019 [US1] Implement `core/src/manager_core/quicksim/squad.py`: `MatchSquad` (XI per research R7, bench of 9 by CA with a second GK), the per-club cache, and an `on_pitch` slot map.
- [X] T020 [US1] Implement `core/src/manager_core/quicksim/engine.py` `simulate_match(home_squad, away_squad, params, rng, neutral) -> (Result, MatchReport)`:
  - the minute loop with stoppage time (R8);
  - shots/xG/on-target/goals with keeper factor (R3);
  - penalties and own goals;
  - fouls and corners (R5, R6);
  - possession;
  - the time trend (R4).

  Scorers and assisters, cards per player and substitutions are delegated to helpers added in US2/US3. US1 uses minimal stand-ins: the scorer is the best finisher on the pitch; there are no substitutions; card totals come from per-side counts. The `Result` card totals are always filled.
- [X] T021 [US1] Implement `core/src/manager_core/quicksim/provider.py` `QuickSimProvider(dataset, params=None)`: `play` (source `quick_sim`) and a temporary `shootout` at 0.752 (replaced in US4). Make it the default in `api.start_season`.
- [X] T022 [US1] Implement the calibration core: `core/src/manager_core/calibration/samples.py` (league sample = 12 clubs double round-robin via 002's `build_group_fixtures`; Mineiro sample = full seasons; fixed seed labels per research R10), `metrics.py` (every metric id) and `harness.py` (`run(dataset, gate, params=None, baseline=None) -> CalibrationReport`, canonical JSON).
- [X] T023 [US1] Write `core/tools/tune_quicksim.py`: coordinate descent on the primary targets over the PR sample, printing each step and writing `model.toml`. Run it and commit the fitted parameters (`model_version = "1.0"`).
- [X] T024 [US1] Gate test `core/tests/integration/test_calibration_gate.py`:
  - the PR gate passes every primary target (SC-001);
  - two runs produce byte-identical JSON (SC-003);
  - a deliberately broken parameter (shot rate × 2) makes the gate fail and name `goals_per_match`;
  - the milestone gate passes as a `slow` test (SC-002).

**Checkpoint**: seasons play with calibrated scorelines. MVP.

---

## Phase 4: User Story 2 - A match report line for every match (P2)

### Tests (first)

- [X] T025 [P] [US2] Unit tests `core/tests/unit/test_quicksim_players.py`, over 5,000 matches:
  - forwards score the largest share of goals, then attacking midfielders, then defenders, and goalkeepers never score;
  - an assister is never the scorer;
  - the assist rate on open-play goals is 70–80%;
  - the penalty taker is the on-pitch player with the best penalty_taking;
  - cards go mostly to defenders and midfielders, and a player with aggression 20 is booked more often than one with 5.
- [X] T026 [P] [US2] Contract test `core/tests/contract/test_cli_season_match.py`:
  - `season match <id>` exits 0, prints every stat label, and every goal line has a minute and a scorer;
  - an unknown id exits 3;
  - with `--date` before the match, it prints "Ainda não disputado";
  - `season scorers` prints the documented columns, ordered by goals;
  - `season fixtures` lines include the match id.

### Implementation

- [X] T027 [US2] In `core/src/manager_core/quicksim/engine.py`, add scorer, assister and penalty-taker selection (research R7) and per-player cards with second yellow → red (R5). The `Result` card totals follow the counting rule in data-model.md.
- [X] T028 [US2] Facade `match_report`, `season_scorers` (`ScorerRow`, order per contracts/facade.md) and the CLI `season match` and `season scorers`, plus match ids in the `season fixtures`/`day`/`bracket` lines (contracts/cli.md), in `core/src/manager_core/api.py` and `cli.py`.

**Checkpoint**: any match can be inspected; the top-scorer list exists.

---

## Phase 5: User Story 3 - Game state changes the match (P3)

### Tests (first)

- [X] T029 [P] [US3] Behaviour tests `core/tests/unit/test_quicksim_game_state.py`, statistical, with fixed seeds and bands:
  - goals by 15-minute period: 76–90+ is the highest and 1–15 the lowest;
  - after minute 75, a side trailing by 1 has a higher shot rate and concedes more than in level games of the same strength gap;
  - a side down to 10 men takes fewer points than matched games without a red;
  - substitutions: 3–5 per side on average, never more than 5, never more than 3 windows plus half-time, no returning player;
  - **caution A/B (SC-006)**: with `caution.enabled`, booked players' second-yellow rate is ≥ 25% lower than without it, and goals conceded by sides with a booked player rise (the trade-off is > 0).

### Implementation

- [X] T030 [US3] In `core/src/manager_core/quicksim/engine.py`, add game state per research R4 (chasing, protecting a lead, red-card rating recomputation, man-up bonus), the caution behaviour per R5 (on/off by parameter) and substitutions per R7. Re-run `tune_quicksim.py` and commit the refit parameters (`model_version = "1.1"`).
- [X] T031 [US3] Add the behaviour check to the harness report (second-yellow rate and goals conceded, caution on vs off), in `core/src/manager_core/calibration/harness.py`.

**Checkpoint**: late goals, comebacks, red cards and caution exist, and the gate still passes.

---

## Phase 6: User Story 4 - Penalty shootouts decided by the players (P4)

### Tests (first)

- [X] T032 [P] [US4] Unit tests `core/tests/unit/test_quicksim_shootout.py`:
  - only the finishers (from `last_result.report`) kick;
  - the order is by penalty_taking, then composure, then id, and it restarts after every eligible player has kicked;
  - 5 kicks each plus sudden death, consistent with 002's `Shootout` validation;
  - conversion over 20,000 kicks is in 70–80%;
  - top-quartile takers convert more often than bottom-quartile ones;
  - a better keeper lowers conversion;
  - with `last_result=None`, it falls back to the XI and still works.

### Implementation

- [X] T033 [US4] Implement `core/src/manager_core/quicksim/shootout.py` per research R11 and wire it into `QuickSimProvider.shootout`. Show the kicks with their takers in `season match` for the last leg.

---

## Phase 7: User Story 5 - The owner runs the calibration (P5)

### Tests (first)

- [X] T034 [P] [US5] Contract test `core/tests/contract/test_cli_calibrate.py`:
  - `calibrate` exits 0 and prints every target id's description with value, target, band, verdict and source, plus the versions and model hash;
  - `--write PATH` writes the JSON, and `--baseline PATH` adds the "antes" column;
  - with a targets file where goals must be 9–10 (test hook: `MANAGER_CALIBRATION_TARGETS`), it exits 1 and names the metric.

### Implementation

- [X] T035 [US5] Implement the `calibrate` command and the `run_calibration` facade in `core/src/manager_core/cli.py` and `api.py`. Generate and commit `core/calibration/quicksim-baseline.json` from the PR gate.

---

## Phase 8: Polish

- [X] T036 [P] Update `docs/roadmap.md` (003 done, 004 next; a note for 007: cross-validate against the quick sim using the same targets file) and the `README.md` quick start (`season match`, `season scorers`, `calibrate`).
- [X] T037 Make sure `ruff check .`, `mypy` (strict) and the full pytest suite pass, including `slow` (milestone gate and 1,000 seasons).
- [X] T038 Run [quickstart.md](quickstart.md) on Windows and note any deviations.
- [X] T039 Open the PR `003-quick-sim` with the PR-gate calibration report (before = placeholder metrics, after = quick sim), the test results and the quickstart check.

---

## Dependencies & Execution Order

- Setup → Foundational → US1. Every later story needs US1's engine and harness.
- US2, US3 and US4 depend on US1 and touch `engine.py`, so they run in sequence: US2 → US3 → US4.
- US5 needs the harness from US1 (T022) and can run after US1, in parallel with US2–US4.
- Polish comes last.

## Parallel examples

```text
Foundational tests: T003 | T004 | T005 | T006, then T007 | T008 | T009 | T010 | T011
US1 tests:          T014 | T015 | T016 | T017 | T018
```

## Implementation Strategy

1. **MVP (stage 1)**: Setup + Foundational + US1. Every match has a calibrated quick-sim result, and the gate passes.
2. **Stage 2**: US2 + US3. Match reports, player events and game state, with a refit.
3. **Stage 3**: US4 + US5 + Polish → PR.
