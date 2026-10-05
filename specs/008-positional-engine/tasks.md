# Tasks: Positional Match Engine

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/live-match.md](contracts/live-match.md)

**Tests**: required (Constitution IV). Behaviour tests run on paired seeds with bands.

## Phase 1: Engine skeleton (US1)

- [x] T001 [US1] `positional/params.py` and `reference/positional/model.toml` (every engine constant as data); `positional/pitch.py`: dimensions, geometry helpers, zones, and the xG logistic model (R3), tested against reference xG values (penalty spot, 16 m central, 25 m).
- [x] T002 [US1] `positional/state.py`: player, ball, team and clock state. Movement steering with top speed and acceleration from pace and acceleration, tested for distance covered.
- [x] T003 [US1] `positional/shape.py`: tactical targets from the formation slot, phase (IP or OOP), ball position, line height, width and compactness, and role offsets. Tests: a higher defensive line gives a higher average target; the block slides towards the ball.
- [x] T004 [US1] `positional/decide.py` part 1: on-ball options (pass, dribble, shoot, cross, clear, hold) with scoring and noisy choice; pass success with interception lines; shot resolution with xG, finishing and the keeper. Unit tests for each.
- [x] T005 [US1] `positional/engine.py` `LiveMatch`:
  - kick-off and restarts (throw-in, goal kick, corner, free kick);
  - halves and stoppage time;
  - goals and the score;
  - events into the 003 `MatchReport` format;
  - deterministic stepping from the seed;
  - `play()` to full time.

  Tests: a whole match runs, the report is valid, and the same seed gives the same match.
- [x] T006 [US1] `positional/record.py`: 2 Hz sampling, int16 cm encoding, zlib; decode round trip. Test: the record covers the whole match, and every event points to a sample.

## Phase 2: The football (US4)

- [x] T007 [US4] Duels: pressing and marking roles from the shape; tackles; dribbles; fouls (aggression, the tackling instruction, 003 caution); cards (the 003 models applied to real fouls); penalties. Behaviour test: booked players commit fewer fouls.
- [x] T008 [US4] Keepers (shot stopping, claiming crosses, distribution per instruction) and set pieces (corner and free-kick setups and takers from 006).
- [x] T009 [US4] Energy and fatigue (R4) and the assistant's substitutions. Tests: realistic distances; a lower late sprint share; tired players lose more duels.
- [ ] T010 [US4] Game-state intents (chase, protect, level, relaxed after a two-goal lead) and the positional meaning of the 006 options (line, engagement, width, tempo, directness, pressing, roles). Paired-seed tests per behaviour.

## Phase 3: Calibration (US2)

- [ ] T011 [US2] Positional samples in the harness (PR 300 matches with robust metrics, milestone 1,500 with all targets); `calibrate --engine positional`; `tools/tune_positional.py`; fit until both positional gates pass.
- [ ] T012 [US2] Cross-validation (the same fixtures through both engines, the SC-003 tolerances) in the milestone gate.
- [ ] T013 [US2] The 3-goal mechanism (R5): measure it in the engine, port it to the quick sim (the leading side relaxes after two goals while the trailing side keeps pushing), refit the quick sim, and pass both quick-sim gates with unchanged targets.

## Phase 4: Career and live play (US1, US3)

- [x] T014 [US1] The provider's precomputed result slot; the user club's matches are played positionally when nothing is precomputed; old saves are unaffected.
- [x] T015 [US3] Live matches in the facade and the server (contract 1.2):
  - `match.start`, `advance`, `state`, `substitute`, `tactic`, `finish`;
  - decisions recorded and validated (substitution rules, 006 validation);
  - replay test (SC-005).
- [x] T016 [US1] Save format v4 with the `records` table and a v3 → v4 migration; the record is stored at `match.finish`; the facade reads it back.

## Phase 5: Clients (US5)

- [x] T017 [US5] The Godot match day drives `match.advance` at the chosen speed. Pause (button and Space) shows the state, and the substitution and tactics panels apply changes. Pilot tests.
- [x] T018 [US5] The same in the terminal UI, with pilot tests.

## Phase 6: Polish

- [ ] T019 Docs (README, roadmap, quickstart, research outcomes); full suites; all gates (both engines, plus cross-validation); ruff and mypy; then the PR. Ask the owner before merging.

## Progress notes (2026-10-05)

- T002–T004 are implemented inside `positional/engine.py` (state, shape and decisions as
  `LiveMatch` methods) rather than separate `state.py`, `shape.py` and `decide.py` modules: the
  per-step code shares a lot of state, and splitting it can wait until the engine settles.
- T010 is in progress. The engine read only 7 of 32 team instructions. Implemented so far: line,
  engagement, width, directness, pressing trigger, tackling, shots from distance, tempo,
  attacking and defensive transitions, build-up strategy, patience, and the forward-runs player
  instruction (with role locks). Still to map: the remaining team and player instructions and
  the roles.
- Calibration findings that changed the engine (T011): fouls concentrated on pressing strikers
  (challenges are now events with a cooldown); the ball was in play 81 minutes with almost no
  throw-ins (clearances and tackles can go into touch, wide players carry down the line, and one
  restart scale); players sprinted all match (urgency-based movement); a high line was never
  punished (balls in behind for runners). `tools/positional_exploit.py` checks tactical balance
  as spec 006 does for the quick sim.
- T013: the relaxed-leader mechanism does not raise the 3-goal share in the engine (17.6% with
  it, 19.3% without, real 24.5%), so R5's hypothesis is not confirmed. The engine's own spread
  is too wide (var/mean 1.21, real 0.89), because totals depend on the fixture (between-fixture
  variance 0.76, quick sim 0.10), driven by tactical imbalance. This is being fixed first.

## Dependencies

- T001 → T002 → T003 → T004 → T005 → T006 → T007–T010 → T011–T013.
- T014–T016 need T005.
- T017 and T018 need T015.
