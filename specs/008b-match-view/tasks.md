# Tasks: 2D Match View

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/local-api.md](contracts/local-api.md)

Tests are written with each task (Constitution IV). `[P]` can run in parallel with its
neighbours.

## Phase 1: The record on the wire (core)

- [x] T001 Shot marks: `shots` in `PositionalRecord` (optional in the header, old blobs decode);
  the engine appends `(sample, slot, on_target)` where it counts a shot, recording only. Tests:
  encode and decode with and without `shots`; a match's report and samples are identical to the
  committed engine's on 3 seeds; every counted shot has a mark.
- [x] T002 `PositionalRecord.chunk(first)` and the wire form (base64 int16 little-endian). Test:
  the chunks of a match advanced in uneven steps concatenate to `match.record()`.
- [x] T003 [P] `positional/view.py` and `reference/match_view.toml`: kits with the clash rule,
  keeper kits, shirt numbers, the pitch description of a match. Tests: every pair of sample
  clubs gets distinguishable kits; the rule is deterministic; numbers are unique per side.
- [x] T004 `api.live_frames`; `match.start` and `match.state` with `pitch` and `time_s`;
  `match.advance` with `frames`; contract 1.4 in `contracts/local-api.md`. Tests: contract tests;
  a match played with frames equals one played without (SC-004).

## Phase 2: The live pitch (US1)

- [x] T005 [US1] `client/scenes/match/playback.gd`: decode chunks, buffer, playhead, speed,
  interpolation, no interpolation across off-pitch or a substitution, marks by sample, score and
  clock at the playhead. Headless tests in `client/tests/test_playback.gd`.
- [x] T006 [US1] `client/scenes/match/pitch.gd`: markings in 105 × 68 proportions at any size,
  discs with numbers in kit colours, keepers, the ball, the marks (goal, card, substitution).
- [x] T007 [US1] `match_day.gd`: the pitch above the feed line, the speeds 1× 2× 4× 8×, Campo /
  Texto with the choice remembered, the feed and stats one action away. Screen tests and a
  screenshot.

## Phase 3: Pause and manage on the pitch (US2)

- [x] T008 [US2] Pause plays the buffer out and freezes; substitutions and the tactics screen from
  the pitch; resume. Test: the decision's time equals the moment on screen.
- [x] T009 [US2] Disc selection: name, position, energy, cards.

## Phase 4: Replay (US3)

- [x] T010 [US3] `api.match_replay` and `match.record` (pitch, frames, events with the running
  score, passages, final score; `null` without a record). Tests: after save and load; an older
  season; a background match.
- [x] T011 [US3] `replay.gd`: timeline with event marks, drag to seek, jump to goals, cards and
  penalties (a few seconds before), speeds, pause; no match controls. Headless tests of seeking.
- [x] T012 [US3] Entry points: Rever after full time and on the user's played matches in the
  calendar, only when the match has a record.

## Phase 5: Highlights (US4)

- [x] T013 [US4] Passages from marks in `positional/view.py` (kinds, lead-in, lead-out and merge
  gap from data). Tests: merging; the edges of a half; a record without shot marks.
- [x] T014 [US4] The scout and `api.live_passages`; `match.passages`. Tests: the passages reported
  live, chunk by chunk, equal the finished record's passages; the match is identical with and
  without the scout (SC-008); a decision rebuilds the scout and later passages follow the new
  match.
- [x] T015 [US4] The passage player in `playback.gd` and both screens: Jogo completo / Melhores
  momentos, the fast clock and the feed between passages, pause between passages, switching
  modes in mid-match, half-time and full time. Headless tests; time a whole match (SC-007).

## Phase 6: Polish

- [ ] T016 Screenshots; README, roadmap and quickstart; both suites; ruff and mypy; the positional
  PR gate unchanged; then the PR. Ask the owner before merging.
