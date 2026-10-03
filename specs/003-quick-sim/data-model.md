# Data Model: Quick Sim (003)

Builds on 001 (`Player`, `Club`, `Formation`, best XI) and 002 (`Result`, `Shootout`,
`ResultProvider`, `MatchContext`, `Season`). Every object below is immutable once a match ends.
The mutable state lives only inside the simulation of one match.

## Changes to 002 objects

| Object | Change |
|---|---|
| `Result` | + `report: MatchReport \| None` (None for the placeholder). Card totals are filled for quick-sim results: yellows include both yellows of a sent-off player, and reds include the dismissal (research R5). |
| `MatchContext` | + `neutral: bool = False`: no home advantage when true. |
| `ResultProvider.shootout` | + keyword `last_result: Result \| None = None`: the provider reads the players on the pitch at the final whistle from `last_result.report`. |
| `Season` | Sets `neutral` for matches of `venue = "neutral"` stages and passes `last_result` to `shootout`. The default provider is `QuickSimProvider`. |

## Model parameters (`reference/quicksim/model.toml`)

| Entity | Fields |
|---|---|
| ModelParams | model_version; base rates (shot, foul, corner, penalty, own-goal share, yellow per foul, direct red per foul); slopes (β_att, β_ctl, β_gk, xG median and spread); home factors (shot, possession); time trend (start, end); game state (δ_chase, δ_exposed, δ_protect, δ_man_up); caution (enabled, κ_foul, κ_card, κ_cost); stoppage ranges; substitution windows; scorer/assister line weights; shootout coefficients. `params_hash` = SHA-256 of the canonical TOML. |

Validation: every value present and of the right type; rates in (0, 1); ranges ordered. A bad
file raises `ModelParamsError` with the key path (same style as 002's R-codes, code `Q001` for
a missing or invalid key).

## Team side (inside one match)

| Entity | Fields |
|---|---|
| MatchSquad | club_id, formation, xi (slot position → player id), bench (player ids, ≤ 9), on_pitch (slot → player id), used_subs, sent_off (ids) |
| TeamRatings | attack, control, defence, goalkeeping, set_pieces, discipline (floats on the 1–20 scale); recomputed when `on_pitch` changes |
| PlayerMatchState | player_id, slot position, on_from (minute), off_at (minute or None), yellows (0–2), red (bool), booked_caution_active (bool) |

## Match output

| Entity | Fields |
|---|---|
| Minute | (base, added): `(37, 0)` is minute 37 and `(90, 4)` is shown as "90+4". It is ordered by (base, added). |
| MatchEvent | minute, side (`home` / `away`), kind (`goal`, `own_goal`, `penalty_goal`, `penalty_miss`, `yellow`, `second_yellow`, `red`, `sub`), player_id, other_player_id (assister, or the player coming on), xg (goals) |
| SideStats | goals, shots, shots_on_target, xg (rounded to 2 dp), possession (int %), corners, fouls, yellows, reds |
| MatchReport | home: SideStats, away: SideStats, events (ordered by minute, then sequence), lineups (starting XI and bench per side), finishers (players on the pitch at the final whistle per side), stoppage (first half, second half), model_version |

**Invariants** (tested on every simulated match, SC-005):
- `goals ≤ shots_on_target ≤ shots` per side. Own goals count for the scoring side's goals, not
  its shots.
- Home and away possession sum to 100.
- Every event player was on the pitch for that side at that minute. The exception is an own
  goal, where the player belongs to the conceding side.
- No player has more than 2 yellows or more than 1 red. A second yellow implies a red. A sent-off
  player has no later events.
- `Result.home_goals == report.home.goals` (and likewise for away), and card totals equal the
  per-player counts.
- At most 5 substitutions per side, in at most 3 windows plus half-time. A player who came off
  does not return.

## Calibration

| Entity | Fields |
|---|---|
| CalibrationTarget | id, description_key (i18n), sample (`league` / `mineiro`), kind (`primary` / `secondary`), target, low, high, unit (`ratio` / `per_match` / `per_side`), source, retrieved (date) |
| SampleSpec | gate (`pr` / `milestone`), league_seasons, mineiro_seasons, seed label |
| MetricResult | target id, value, verdict (`pass` / `fail` / `warn`), baseline value (optional) |
| CalibrationReport | core_version, python_version, model_version, params_hash, gate, sample sizes (matches per sample), results (`MetricResult`s in target order), behaviour check (second-yellow rate and goals conceded with caution on and off), passed (bool) |

The report JSON is canonical (sorted keys, fixed float precision of 4 dp), so the same inputs
give byte-identical files (SC-003).
