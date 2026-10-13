# Research: 2D Match View

## R1. What the record holds (read from the code, 2026-10-13)

- 2 samples a second; each is the ball (x, y, z) and 22 (x, y) in centimetres, int16; a slot not
  on the pitch is (−1, −1). Slots 0–10 are home, 11–21 away.
- Positions are absolute. The sides change ends at half-time in the engine, so the record shows
  it and the view never mirrors.
- **z is always 0.** The engine has no ball height. Decision: the ball is drawn flat; the spec's
  ball-height requirement was removed.
- Events are (sample, index into the match report's events). The engine's event kinds are
  `goal`, `own_goal`, `penalty_goal`, `penalty_miss`, `yellow`, `second_yellow`, `red` and `sub`.
  **A saved shot is not an event**; only the team counters know about it.
- Substitutions are (sample, slot, incoming player id).

## R2. Shot marks

- **Decision**: the engine appends `(sample, slot, on_target)` to a `shots` list where it counts
  a shot, in recording mode only. No random draw, no change to the report.
- **Why**: highlights need the saved shots. A test compares the report and the samples of a
  match with the marks against the committed engine's.
- **Rejected**: shot events in the match report (changes stored reports and the feed); deriving
  shots from ball speed in the samples (a guess, and a rule in the client).
- **Old records**: `shots` is optional in the header. Their highlights have no saved shots.

## R3. The wire form

- **Decision**: samples travel as base64 of the int16 little-endian values, 47 a sample, with the
  first sample's index. Godot decodes with `Marshalls.base64_to_raw` and `to_int16_array`.
- **Why**: a whole match is about 10,800 samples: 1 MB as bytes, against 2.5 MB of JSON numbers
  that Godot would parse into Variants. A live chunk is small either way, and one form for both
  keeps one decoder (the spec's "same form").

## R4. Live playback and the pause moment

- The client asks for the match in small chunks (1 s of match time at 1×; at most 4 s) and keeps
  a playhead that runs behind the last sample received. It interpolates between two samples.
- **Pause**: the client stops asking, plays the buffer out (at most one chunk) and freezes, so the
  moment on screen is the engine's moment when the owner acts. Decisions are stamped by the core
  as today.
- **Speeds on the pitch**: 1×, 2×, 4× and 8× of real time. The text view keeps its own (30× and
  up): they are not watchable on a pitch.
- **No interpolation** across a slot that is off the pitch at either sample, or across a
  substitution in that slot: the disc disappears and appears.

## R5. Highlights without spoilers

- **Passages** are computed in the core from marks: for each highlight (goal, own goal, penalty
  goal or miss, red, second yellow, shot on target) the span from `lead_in_s` before to
  `lead_out_s` after, merged when closer than `merge_gap_s`. Values are data
  (`reference/match_view.toml`): 10 s, 4 s and 8 s to start with.
- **Live look-ahead (the scout)**: a second `LiveMatch` from the same seed with the decisions so
  far, recording, advanced up to a horizon ahead of the real match. `match.passages` returns the
  passages between the real match's time and the scout's.
- **A decision** makes the scout stale. It is rebuilt lazily from the seed and the decisions and
  advanced to the real match's time. This is the replay path that spec 008 already tests.
  Cost: at most one match's simulation (1–2 s) per decision, in highlights mode only.
- **Rejected**: deep-copying the live match (it reaches the dataset and the parameters; identity
  of the copy would need its own proof); running the real match ahead (R4's pause moment breaks).
- **Between passages** the client advances the real match without frames at 60× and shows the
  feed; it switches to frames at the passage start. The client knows a passage is coming and
  shows nothing of it.

## R6. Kits

- Club colours come from the dataset (contract 1.3 already sends them). The core resolves the
  kits for a match: home in its colours; away in its colours unless the two primaries are closer
  than a threshold (distance in RGB, data), then away in its secondary, then in a neutral kit.
- Goalkeepers: a fixed keeper kit per side that clashes with neither outfield kit.
- Shirt numbers: the dataset's `shirt_number`, else the slot's number in the team sheet (1–11),
  and the next free number for a substitute.
- For a past season's replay the kits are resolved again from the dataset: club colours do not
  change in Milestone 0.

## R7. FM benchmark

FM's 2D classic view: discs with numbers, a flat ball with a shadow when high, a scoreboard, one
commentary line, speed and highlight settings, pause into the tactics screen, and a post-match
replay with event markers. This plan follows it except for ball height (R1) and the three
highlight levels (one here, by owner decision).
