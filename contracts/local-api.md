# Contract: Local API, version 1.2

The client starts the core as a child process:

```text
pythonw.exe -m manager_core.server --saves <folder>
```

Both sides then exchange **one JSON object per line**, UTF-8, over the child's stdin and stdout
(research R1). The core writes nothing else to stdout. Logs go to stderr.

## Messages (a JSON-RPC 2.0 subset)

```json
{"jsonrpc": "2.0", "id": 7, "method": "career.continue", "params": {"to_season_end": false}}
{"jsonrpc": "2.0", "id": 7, "result": {"kind": "user_match", "day": "2027-01-17", "match_id": "primeira-fase-r01-03"}}
{"jsonrpc": "2.0", "id": 8, "error": {"code": "S001", "message": "Fulano está suspenso e não pode ser escalado.", "data": {"issues": [...]}}}
{"jsonrpc": "2.0", "method": "progress", "params": {"request": 9, "day": "2027-02-03", "played": 41}}
```

- **Requests**: `id` is a positive integer chosen by the client. Requests are handled one at a
  time, in arrival order.
- **Results** are plain JSON:
  - a dataclass becomes an object, with field names as they are in the core;
  - an enum becomes its value;
  - a date becomes ISO `YYYY-MM-DD`;
  - a tuple becomes an array;
  - floats are kept as they are.
- **Errors**: `code` is a string (the core's code, or one of the protocol codes below).
  `message` is PT-BR, ready to show. `data` is optional.
- **Notifications** (no `id`) go from the core only. Version 1.0 has only `progress`.

**Protocol error codes**:

| Code | Meaning |
|---|---|
| `P001` | bad JSON or a bad message shape |
| `P002` | unknown method |
| `P003` | bad parameters (missing, or of the wrong type) |
| `P004` | no career is open, for a method that needs one |
| `P005` | internal error (the message names it; the core keeps running) |
| `NOT_FOUND` | the facade's `NotFoundError` (`data`: kind, id) |

## Versioning

`MAJOR.MINOR`:
- adding a method or a result field is a minor change;
- removing or renaming anything, or changing a meaning, is a major one.

The client refuses to run on a different major version (spec FR-005).

History: 1.0 (spec 007); 1.1 adds `tactic.set_role` (the role-change rule moved from the clients
into the core); 1.2 adds the live-match methods (spec 008); 1.3 adds `club_colors` to
`CareerStatus` (the user club's primary and secondary colours, `#RRGGBB`, which the client's
look uses); 1.4 adds what the 2D match view draws (spec 008b): `pitch` in `match.start`,
`frames_from` in `match.advance`, `time_s` in `LiveState`, `match.record`,
`match.passages`, and `user_match_replay` in the calendar's days.

**Packaging note**: the server finds the repo (saves, sample data) from its source location
(`server/__main__.py`, `parents[4]`), so it runs from a source checkout. An installed package
will need `--saves` and `--data` passed explicitly; revisit when the game is packaged.

## Methods

"→" gives the result. All parameters are named (`params` is an object).

### Session

| Method | Params | → | Notes |
|---|---|---|---|
| `hello` | `client: str` | `{contract, core_version, model_version, strings}` | `strings`: the whole PT-BR i18n catalogue (R4): `ui.*`, months, weekdays, table headers, attributes… |
| `shutdown` | — | `{saved: bool}` | saves the open career, then the core exits |

### Careers

| Method | Params | → | Facade |
|---|---|---|---|
| `career.list` | — | `[SaveSummary]` | `list_saves` |
| `career.clubs` | — | `[{id, name, reputation}]` | the sample world's clubs, for a new career |
| `career.new` | `name, club_id` | `CareerStatus` (it is now open) | `new_career`, then `save_career` |
| `career.open` | `name` | `{status: CareerStatus, notices: [str]}` | `load_career` |
| `career.save` | — | `{path}` | `save_career` |
| `career.status` | — | `CareerStatus` | `career_status` |
| `career.continue` | `to_season_end: bool = false` | `Stop` | `continue_career`; sends `progress` while running |

### Team selection

| Method | Params | → | Facade |
|---|---|---|---|
| `selection.current` | — | `{selection, positions, squad: [SquadRow]}` | the confirmed selection if valid, else `propose_selection` |
| `selection.propose` | `formation?: str` | `Selection` | `propose_selection` |
| `selection.swap` | `selection, slot, player_id` | `Selection` | `swap_in_selection` (not validated) |
| `selection.validate` | `selection` | `[SelectionIssue]` | `validate_selection` |
| `selection.confirm` | `selection` | `{issues: [SelectionIssue], tactic_changes: [str]}` | `tactic_changes`, then `confirm_selection` (errors → `SELECTION`) |
| `formations.list` | — | `[{name, positions: [str]}]` | `list_formations`, `formation_positions` |

### Tactics

| Method | Params | → | Facade |
|---|---|---|---|
| `tactic.options` | — | `Options` | `tactic_options` |
| `tactic.current` | — | `Tactic` | `current_tactic` |
| `tactic.default` | `formation` | `Tactic` | `default_tactic` |
| `tactic.suggest_oop` | `formation` | `[str]` | `suggest_oop_formations` |
| `tactic.roles` | `position, phase` | `[Role]` | `valid_roles` |
| `tactic.suitability` | `pairs: [[player_id, role_id]]` | `[float]` | `role_suitability`, one per pair |
| `tactic.set_role` | `tactic, slot, phase, role_id` | `Tactic` | `set_role`: the slot's role changed, instructions the new roles lock dropped (since 1.1) |
| `tactic.validate` | `tactic` | `[TacticIssue]` | `validate_tactic` |
| `tactic.confirm` | `tactic` | `{}` | `confirm_tactic` (issues → `TACTIC`, `data.issues`) |

### Live matches (since 1.2, spec 008)

The client drives the clock: it calls `match.advance` at its chosen speed, and pausing is not
calling it. The assistant handles the user's substitutions until his first decision.

| Method | Params | → | Notes |
|---|---|---|---|
| `match.start` | — | `{match, side, pitch, feed, state, finished}` | The pending user match (stop `user_match`), built exactly as the match day would build it. `pitch` since 1.4. |
| `match.advance` | `seconds`, `frames_from?` | `{feed, state, finished, frames?}` | `feed` holds only the lines not sent before. With `frames_from` (a sample index, since 1.4) it adds `frames`: the positions from that sample on. |
| `match.state` | — | `LiveState` | Minute, half, score, stats so far, players on the pitch (energy, yellow), bench, substitutions and windows left, at half-time, the current tactic, and `time_s` (the match clock in seconds, since 1.4). |
| `match.substitute` | `off, on` | `LiveState` | From now on. Errors `MATCH` with `match_code`: `sub_limit`, `sub_window`, `sent_off`, `not_on_pitch`, `not_on_bench`, `finished`. |
| `match.tactic` | `tactic` | `LiveState` | From now on; the in-possession formation stays the selection's (`formation_change`); 006 validation (`TACTIC`). |
| `match.finish` | — | `{stop, match_id}` | Plays to full time, commits the result, continues the match day; the next stop. |

A live match is never saved half-played: `career.continue` or closing drops it, and the career
resumes before that match day.

**The 2D view's data (since 1.4, spec 008b).** Reading it never changes the match.

- **`pitch`**: `{length_cm, width_cm, hz, home, away}`; each side is
  `{club_id, name, kit: {shirt, number, keeper}, players, bench}` with colours as `#RRGGBB`. A
  player is `{slot, player_id, name, number, keeper}`; `slot` is the record's 0–21 (home 0–10,
  away 11–21) and −1 on the bench. The core chooses the kits: the away side changes colours when
  its shirt would clash with the home one.
- **`frames`**: `{first, count, samples, events, subs, shots}`. `samples` is the base64 of
  `count` samples, each 47 little-endian int16 values in centimetres: the ball (x, y, z), then
  22 (x, y) in slot order; (−1, −1) is "not on the pitch". Positions are absolute: the sides
  change ends at half-time. The origin is the corner of the goal line the home side defends
  first; x runs along the pitch.
  - `events`: `{sample, kind, side, player_id, other_id, score, minute}` (`score` after the
    event);
  - `subs`: `{sample, slot, player_id, name, number}` (the player coming on takes the slot);
  - `shots`: `{sample, slot, on_target}`.
  Every `sample` is an index into the whole match, so chunks asked for end to end
  (`frames_from` = the samples received so far) add up to the stored record.
- **`match.record`** (`match_id?`) → `{match, pitch, frames, clock, final_score}` or `null`: a
  played user match of this season as a replay, with its whole record in `frames`; without
  `match_id`, the live match as played so far. `clock` is `[[sample, minute, added]]` at each
  change of minute. `null` for a match with no positional record; `NOT_FOUND` for an unknown one.
- **`match.passages`** (`horizon_s`) → `{from_s, until_s, passages, finished}`: highlights mode.
  `passages` are the `[start_s, end_s]` spans of match time worth showing (a goal, a shot on
  target, a penalty, a red card, with the seconds before and after) that are not over yet, looked
  for from the match clock `from_s` up to `until_s`. The core looks ahead with a second copy of
  the match; the live match is not advanced. A replay carries its `passages` too.
- **`view.calendar`** days carry `user_match_replay`: whether the day's user match can be
  watched again.

### Views

| Method | Params | → | Facade |
|---|---|---|---|
| `view.home` | — | `{status, last_match?: MatchView, news: [NewsItem] (latest 5)}` | new thin helper (R8) |
| `view.squad` | — | `[SquadRow]` | `squad_view` |
| `view.player` | `player_id` | `PlayerProfile` | `player_profile` |
| `view.table` | `group?: str` | `[TableRow + club_name]` | `season_table` |
| `view.groups` | — | `[{label, clubs}]` | `season_groups` |
| `view.fixtures` | `club_id?: str` | `[MatchView]` | `season_fixtures` |
| `view.calendar` | `month: int` | `[{day, user_match?: MatchView, match_count, windows: [str], events: [SeasonEvent]}]` | `season_calendar` |
| `view.news` | — | `[NewsItem]` | `career_news` |
| `view.match` | `match_id` | `{match: MatchView, feed: [FeedLine], stats: [[label, home, away]]}` | `match_view`, `match_feed`, stat rows (R8) |
| `view.last_user_match` | — | `{match_id?: str}` | `last_user_match` |

### Domain error codes passed through

| Code | From | `data` |
|---|---|---|
| `SELECTION` | `SelectionError` | `issues: [SelectionIssue]` (codes: suspended, not_in_squad, …) |
| `TACTIC` | `TacticError` | `issues: [TacticIssue]` (T001–T005) |
| `SAVE` | `SaveError` | `save_code` (V001–V003, name codes) |
| `NOT_FOUND` | `NotFoundError` | `kind, id` |
| `MATCH` | `LiveMatchError` | `match_code` |

## Guarantees

- **Rules.** The client sends choices only. Every rule, check and number comes from these
  results (Constitution III).
- **Determinism.** The same career, seed and sequence of requests give the same results as the
  facade alone (spec FR-011; tested as parity).
- **Saves.** Only the core writes them. `shutdown` and `career.save` write the open career.
