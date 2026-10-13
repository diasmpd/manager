# Implementation Plan: 2D Match View

**Branch**: `008b-match-view` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

## Summary

The desktop client draws the user's match on a top-down pitch from the positional record
(see [research.md](research.md)).
- **Live**: `match.advance` also returns the record chunk it just played (the samples, events,
  substitutions and shot marks), and the client plays the chunk back with interpolation.
- **Replay**: a new `match.record` method returns a played match's whole record with what is
  needed to draw it (line-ups, kits, events, passages).
- **Highlights**: the core says which passages matter. Live, it looks ahead with a second copy of
  the match (the "scout") built from the seed and the decisions, so the real match is never ahead
  of the screen and pausing works as today.
- **The engine's play does not change.** The record gains shot marks, written in recording mode
  only, with no random draw.

## Technical Context

- **Language**: Python ≥ 3.12 (core, standard library only) and GDScript (Godot 4.7).
- **Contract**: local API **1.4** ([contracts/local-api.md](contracts/local-api.md)): additive.
- **Storage**: no save-format change. The record's header gains an optional `shots` list; records
  without it decode as before.
- **Data**: `reference/match_view.toml` holds the highlight kinds, the lead-in, lead-out and merge
  gap, and the colour-clash threshold.
- **Testing**:
  - Python: chunks concatenate to the final record; a match is identical with and without
    frames and with and without the scout (SC-004, SC-008); passages from the scout equal the
    passages from the finished record; the kit clash rule; the contract methods.
  - Godot headless: playback (interpolation, appearing and disappearing discs, seeking, the
    timeline, the passage player) and the screens.
- **Performance**: a sample is 94 bytes before base64; a whole record is about 1 MB.
  Highlights mode plays the match twice in the core (scout and real): 2–4 s over a match.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Realism measured | ✅ | No simulation system is added. The positional gates must be unchanged: a test compares the report and the samples with the shot marks against the committed engine. |
| II. Determinism | ✅ | Frames, the scout and the view never touch the real match's random stream; tests compare records. The scout is the tested replay path (seed plus decisions). |
| III. Thin client | ✅ | The client interpolates and draws. Kits, the clash rule, the passages and every match rule are the core's, behind contract 1.4. |
| IV. Test-first | ✅ | The Python tests and the headless playback tests are written with each step. |
| V. Manager in control | ✅ | Pause, substitutions and the tactic work in both modes, from the moment on screen. |
| VI. Data rights | ✅ | No data. |
| VII. Incremental | ✅ | Discs and a ball; one highlights level; no ball height, no 3D. |

## Project Structure

```text
core/src/manager_core/
├── positional/record.py     # `shots` in the record; chunk(); the wire form
├── positional/engine.py     # shot marks while recording (no random draw)
├── positional/view.py       # NEW: kits and the clash rule, line-ups, passages from marks
├── reference/match_view.toml  # NEW
├── api.py                   # live_frames, live_passages (the scout), match_replay
├── server/methods.py        # match.advance `frames`, match.passages, match.record; 1.4
client/scenes/match/
├── playback.gd              # NEW: samples buffer, interpolation, playhead, passages (no nodes)
├── pitch.gd                 # NEW: the Control that draws the pitch, discs, ball and marks
client/scenes/screens/
├── match_day.gd             # pitch or text; full match or highlights; speeds; disc info
├── replay.gd                # NEW: a played match: timeline, jumps, highlights
├── calendar.gd              # "Rever" on the user's played matches that have a record
client/tests/test_playback.gd  # NEW
contracts/local-api.md       # 1.4
```

## Phases

1. **Core: the record on the wire**
   - shot marks in the engine and the record;
   - `PositionalRecord.chunk(first)` and the wire form (int16 little-endian, base64);
   - `match.advance` with `frames`; `match.start` with the pitch description (line-ups, kits).
2. **Client: the live pitch (US1)**
   - `playback.gd` and its tests; `pitch.gd`;
   - `match_day.gd`: the pitch above the feed, the pitch speeds, pitch or text.
3. **Pause and manage on the pitch (US2)**: play out the buffer, freeze, the existing panels;
   the disc info.
4. **Replay (US3)**: `match.record`; `replay.gd`; the entry points.
5. **Highlights (US4)**: passages in the core; the scout; `match.passages`; the passage player in
   both screens.
6. **Polish**: screenshots, docs, both suites, the positional PR gate, then the PR.

## Complexity Tracking

| Item | Why it is needed | Simpler alternative rejected |
|---|---|---|
| The scout (a second copy of the live match) | Highlights need to know a shot is coming some seconds before it, without the real match running ahead of the screen | Letting the real match run ahead: the state, the energy and the pause moment would be ahead of what the owner sees, and a decision would need a rewind |
| Shot marks in the record | A saved shot is not a match event, and highlights of goals and red cards alone are about three passages a match | Adding shot events to the match report: it changes reports, feeds and every stored result |
