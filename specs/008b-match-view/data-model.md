# Data Model: 2D Match View

No save-format change.

## Positional record (`positional/record.py`, extended)

| Field | Change |
|---|---|
| `shots` | NEW, optional: `(sample index, slot, on target)` for every shot. Absent in records made before this spec. |

`chunk(first)` gives the samples, events, subs and shots from sample `first` on, with absolute
indices.

## Match view data (`reference/match_view.toml`)

| Key | Meaning | Start value |
|---|---|---|
| `highlights.kinds` | event kinds that make a highlight, plus `shot_on_target` | goal, own_goal, penalty_goal, penalty_miss, red, second_yellow, shot_on_target |
| `highlights.lead_in_s`, `lead_out_s`, `merge_gap_s` | the passage around a highlight | 10, 4, 8 |
| `kits.clash_distance` | two shirt colours closer than this clash | fitted on the sample dataset's clubs |
| `kits.neutral`, `kits.keepers` | the fallback kit and the two keeper kits | — |

## Live session (`api.LiveSession`, extended)

| Field | Meaning |
|---|---|
| `frames_sent` | samples already sent to the client |
| `scout`, `scout_decisions` | the look-ahead match and how many decisions it was built with (stale when the real match has more) |

## Client playback (`client/scenes/match/playback.gd`, in memory)

| Field | Meaning |
|---|---|
| `samples`, `first` | the int16 buffer and the index of its first sample |
| `playhead` | the moment on screen, in samples (fractional) |
| `speed`, `paused` | the owner's choice |
| `marks` | events, subs and shots by sample |
| `passages`, `mode` | full match or highlights, and what is left to show |
