# Contract addition: live matches (local API 1.2)

These methods are added to [contracts/local-api.md](../../../contracts/local-api.md) as minor
version **1.2**, when they are implemented. The client drives the clock: pausing means it stops
calling `match.advance` (research R7).

| Method | Params | → | Notes |
|---|---|---|---|
| `match.start` | — | `{match, state}` | Starts the user's pending match (the stop kind is `user_match`, and the selection is confirmed). Fails with `P004` with no career, and `MATCH` with nothing pending. |
| `match.advance` | `seconds: number` | `{feed: [FeedLine], state, finished: bool}` | Plays up to `seconds` of match time and returns the new feed lines. |
| `match.state` | — | `state` | The minute, score, stats so far, players on the pitch (with energy and cards), the bench, substitutions left, and the current tactic. |
| `match.substitute` | `off, on` | `state` | Valid only while playing. Errors: `MATCH` with codes `sub_limit`, `sub_window`, `not_on_pitch`, `not_on_bench`, `sent_off`. |
| `match.tactic` | `tactic` | `state` | From now on. Errors: `TACTIC` (006 validation). |
| `match.finish` | — | `{report, stop}` | Plays to full time if needed, commits the result, continues the match day, and returns the next stop. |

**`state`** fields:
- `minute`, `added`, `half`, `score`;
- `stats`: the same as `SideStats` so far;
- `on_pitch`: `{player_id, slot, position, energy, yellow}`;
- `bench`;
- `subs_left`, `windows_left`;
- `tactic`.

**Determinism.** The server records each decision with the match time. `match.finish` stores the
match with its decisions, so the same seed and decisions replay it exactly.
