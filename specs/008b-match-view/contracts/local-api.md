# Contract addition: the 2D match view (local API 1.4)

Added to [contracts/local-api.md](../../../contracts/local-api.md) as minor version **1.4**. Every
change is additive: a 1.3 client keeps working.

| Method | Params | → | Notes |
|---|---|---|---|
| `match.start` | — | adds `pitch` | The pitch description of the match (below). |
| `match.state` | — | adds `pitch`, `time_s` | `time_s` is the match time in seconds. |
| `match.advance` | `seconds`, `frames: bool = false` | adds `frames` when asked | The record chunk of what was just played. |
| `match.passages` | `horizon_s: number` | `{from_s, until_s, passages: [[start_s, end_s]]}` | Highlights mode: the passages between the match's time and up to `horizon_s` ahead. Never changes the match. `until_s` is short of the horizon at half-time and full time. |
| `match.record` | `match_id`, `year?` | `{pitch, frames, events, passages, final_score}` or `null` | A played user match. `null` when it has no record. Fails with `NOT_FOUND` for an unknown match. |

**`pitch`**: `{length_cm: 10500, width_cm: 6800, hz, home, away}`; each side is
`{club_id, name, kit: {shirt, number, keeper}, players: [{slot, player_id, name, number, keeper}]}`
(colours as `#rrggbb`; `slot` is the record's 0–21).

**`frames`** (a record chunk): `{first, count, samples, events, subs, shots}`.
- `samples`: base64 of `count × 47` int16 little-endian values: the ball (x, y, z), then 22 (x, y),
  in centimetres; (−1, −1) is "not on the pitch".
- `events`: `[{sample, kind, side, player_id, other_id, score: [h, a]}]`.
- `subs`: `[{sample, slot, player_id, name, number}]`.
- `shots`: `[{sample, slot, on_target}]`.
- Sample indices are absolute, so chunks concatenate to the stored record.

**Determinism.** `frames`, `match.passages` and `match.record` read. The same seed and decisions
give the same match whatever is asked for.
