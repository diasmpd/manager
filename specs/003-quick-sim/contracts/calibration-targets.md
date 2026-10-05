# Contract: Calibration targets file (`reference/calibration/quicksim-targets.toml`)

Aggregate statistics only (Constitution I/VI). One `[[targets]]` table per metric:

```toml
format_version = 1

[[targets]]
id = "goals_per_match"
sample = "league"            # league | mineiro
kind = "primary"             # primary (gate) | secondary (warning)
unit = "per_match"           # per_match | per_side | ratio
target = 2.48
low = 2.28
high = 2.68
source = "Série A 2024 (2,44) e 2025 (2,52), contagem própria (760 jogos)"
retrieved = 2026-10-02
```

Metric ids understood by the harness (an unknown id is an error):

| id | sample | meaning |
|---|---|---|
| `goals_per_match` | league | total goals / matches |
| `home_win`, `draw`, `away_win` | league | share of matches |
| `home_goals`, `away_goals` | league | per match |
| `nil_nil` | league | share of 0–0 |
| `total_goals_0` … `total_goals_4`, `total_goals_5plus` | league | share of matches with that many goals |
| `fav_win`, `fav_draw`, `fav_loss` | league | top-3 v bottom-3 of each simulated season's final table, from the favourite's side |
| `yellows_per_match`, `reds_per_match` | league | both sides |
| `mineiro_draw`, `mineiro_goals_per_match` | mineiro | first-phase matches only |
| `shots_per_match` | league | both sides |
| `shots_on_target_per_side` | league | per side |
| `xg_minus_goals` | league | (xG − goals) per match; target 0 |
| `corners_per_match`, `fouls_per_match` | league | both sides |
| `late_goal_share`, `first_half_goal_share` | league | share of goals after minute 75 / in the first half |
| `shootout_conversion` | mineiro | kicks scored / kicks taken (all shootouts in the sample) |
| `own_goal_share` | league | own goals / goals |

The harness reports every target in file order. It refuses a file whose `low ≤ target ≤ high`
does not hold (code `C001`, with the key path).
