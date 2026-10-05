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
into the core); 1.2 adds the live-match methods (spec 008).

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
| `match.start` | — | `{match, side, feed, state, finished}` | The pending user match (stop `user_match`), built exactly as the match day would build it. |
| `match.advance` | `seconds` | `{feed, state, finished}` | `feed` holds only the lines not sent before. |
| `match.state` | — | `LiveState` | Minute, half, score, stats so far, players on the pitch (energy, yellow), bench, substitutions and windows left, at half-time, the current tactic. |
| `match.substitute` | `off, on` | `LiveState` | From now on. Errors `MATCH` with `match_code`: `sub_limit`, `sub_window`, `sent_off`, `not_on_pitch`, `not_on_bench`, `finished`. |
| `match.tactic` | `tactic` | `LiveState` | From now on; the in-possession formation stays the selection's (`formation_change`); 006 validation (`TACTIC`). |
| `match.finish` | — | `{stop, match_id}` | Plays to full time, commits the result, continues the match day; the next stop. |

A live match is never saved half-played: `career.continue` or closing drops it, and the career
resumes before that match day.

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
