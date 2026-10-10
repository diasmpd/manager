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

## Progress notes (2026-10-09)

- Tuner run 14 left passes (620 a team), crosses (7.7), corners (7.3) and xG per shot (0.135)
  outside their bands. Most of the counted crosses went to an empty box and did nothing (about
  1 a team was real). Fixed: box runs (near post, penalty spot, far post) when the ball is wide
  in the final third, and a cross is offered only with a target, valued by the header.
- Possession diagnostic: about 229 possessions a team (real is roughly half), under 7 s each;
  about 145 a team end in midfield (92 lost passes, 52 lost take-ons). Final-third reach (about
  57 a team) is near real. Midfield is too chaotic: the tuner now has a take-on target, and the
  threat curve's depth term is tunable (`decide.threat_u`). Raising it alone barely moved play
  forward.
- xG per shot is high because shots from beyond about 20 m almost never pass `min_shot_xg`.
- The local Python had lost the editable installs (`pip install -e "core[dev]" -e "tui[dev]"`
  restored them; the desktop client needs them to start the core).

## Progress notes (2026-10-10)

- T011, the harness half: `calibrate --engine positional` runs the positional gates
  (`calibration/positional.py`). The sample is the head of the league sample's fixture list
  (PR 300 matches, milestone 1,500), on the quick sim's match seeds, played in parallel
  processes and merged in fixture order. The PR gate fails only on the robust metrics of
  research R6; the other primary targets warn there and gate at the milestone.
- T012: the milestone gate also plays the same fixtures through the quick sim and compares
  goals per match, the home, draw and away shares and each total-goals share against the SC-003
  tolerances. A miss fails the gate (`cross_validation:<metric>`).
- Decisions to confirm with the owner:
  - The Mineiro sample's three targets (first-phase draws and goals, shootout conversion) are
    not measured for the positional engine: the first phase is the same engine on the same
    clubs, and the shootout is the model both engines share.
  - The positional exploit check is still the dev tool (`tools/positional_exploit.py`), not
    part of the gate.
  - The two gate tests are `milestone`-marked until the engine is fitted. The PR gate then has
    to join the CI run (about 3.5 minutes for 300 matches on 12 threads).
- First PR-gate run, on the model as run 16 was stopped: goals 2.80, home 40.7%, draw 22.0%,
  away 37.3% (home 1.41 and away 1.40 goals), yellows 3.20, reds 0.16, shots 20.9, corners
  6.5, fouls 16.2, late goals 20.8%. The failed-take-on fix removed many duels, so fouls, cards
  and the home edge have to be refitted: tuner run 16 was restarted from that model.
- SC-006 had no tests: T007 and T009 list behaviour tests that were never written. They are
  now in `tests/integration/test_positional_behaviour.py` (card caution, tired duels, the
  relaxed leader, distances and the late sprint share, chasing and protecting, line height and
  width). Measuring them found two behaviours without their trade-off, both fixed in the
  engine:
  - A booked player fouled less and lost nothing. He now also wins the ball less
    (`caution.cost` of spec 003, by his caution strength), as the pain-point log promises.
  - Tired players sprinted as often as fresh ones: the late sprint share rose (0.10 to 0.11).
    Three quarters of all sprinting is the support run in possession, so a tired player now
    lets the play get further ahead before he sprints to join it (`energy.conserve`, 1.0: the
    late share is about 0.77 of the early one). The size of the real decline still needs a
    source, like the passing targets.
  - Not confirmed: "a trailing side concedes better chances" (the leader's xG after minute 70
    was 1.90 against 1.96 level, 6 matches). The line of engagement has no test yet: its effect
    on positions was inside the noise of 3 matches.
- Tuner run 16 was stopped after two steps (attribute spread 0.31 to 0.24, minimum shot xG
  0.051 to 0.039, loss 51.7 to 31.1) so that it fits the engine with the two trade-offs, and
  restarted from there.
- The core suite had become unrunnable: every career a test makes played the user's matches
  on the positional engine (about 50 s a season), so `test_season_suspensions_are_served_100`
  alone took about 70 minutes and the whole run over two hours. Test careers now play the
  user's matches on the quick sim (an autouse fixture in `tests/conftest.py`), and a test about
  the user's matches themselves asks for the engine with `@pytest.mark.positional`: the live
  match tests, the SC-004 season budget and one career of the suspension check. To confirm with
  the owner: this is less implicit coverage of positional seasons in exchange for a suite that
  runs in minutes.
- The tuner's `--low-priority` never worked on 64-bit Python: the priority call failed without
  a word (a truncated process handle), so the long runs took the whole PC. Fixed, with a
  regression test (`tests/unit/test_tools.py`). The earlier note that Windows does not pass a
  lowered priority on to child processes was this same failure: it does.
- Tuner run 16 round 1 on the engine with the trade-offs: loss 54.3 to 27.5, home advantage
  back (1.49 home, 1.19 away goals). What it left is structural, and one parameter at a time
  cannot reach it (measured on the tuner's 132 fixtures):
  - **Fouls and restart time move together.** Fouls were 14.7 (target 26), so yellows 3.1
    (5.2), and the ball was in play 49.6 minutes: more fouls alone means more dead time. The
    restart scale was set by hand for a match with too few stoppages. `duel.foul_base` 0.34
    with `restarts.scale` 1.30 gives fouls 24.9, yellows 5.0 and 54.1 minutes in play.
  - **Players almost never shot from distance**: 27% of shots from outside the box, none beyond
    25 m, 7.8 a match from 5 to 10 m, 78% with nobody in the shooting lane. An attack went on
    until it made a close chance or lost the ball. `decide.min_shot_xg` 0.039 to 0.025 gives
    45% from outside the box, xG per shot 0.115 (0.131) and corners 9.4 (7.3).
  - With both, goals rise to 3.31 (xG 3.30 from 28.7 shots): more live play, and the same
    close chances. This candidate is **not** the committed model (the owner's matches would be
    too high-scoring until a refit): the tuner runs from it in the tuner worktree, and its
    result is brought over only if the gate is better for it.
  - **Red cards are the wrong kind**: 0.44 second yellows and 0.04 straight reds a match (the
    target is 0.25 in all). About one booked player in ten is sent off, so fouls are
    concentrated on too few players. Next: the fouls-per-player distribution, and a source for
    the real split of second yellows and straight reds.
  - Still structural: passes 693 a team (420), crosses 2.9 (14), take-ons 27 (19).
  - Tried and removed: a centre-back stepping into the shooting lane near the box. It took
    away long shots (the blocked shot is not attempted) and total shots (22.7 to 19.6), left
    the close ones (7.8 to 6.4 from 5 to 10 m) and did not move xG per shot (0.127).
- Tuner: the yellow-card target weighs 1.0 (it is a primary gate target), and the foul-rate
  bound is 0.45 (26 fouls need about 0.34).
- A positional match takes about 3.4 s on the home PC (budget 10 s). `test_a_season_is_fast`
  (spec 004, 5 s) had been failing since the user's matches moved to the positional engine (a
  season took 48 s). It now measures the day loop with the user's matches on the quick sim,
  and a new test holds SC-004 (a season with positional matches in at most 2 minutes).

## Dependencies

- T001 → T002 → T003 → T004 → T005 → T006 → T007–T010 → T011–T013.
- T014–T016 need T005.
- T017 and T018 need T015.
