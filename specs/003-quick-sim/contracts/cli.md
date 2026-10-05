# Contract: CLI additions (003)

All output in pt-BR. Exit codes as in 002: 0 ok; 1 invalid input or calibration failed; 2 usage;
3 not found.

| Command | Output |
|---|---|
| `season match <MATCH-ID>` | The match's date, venue and score. Then a two-column stat line (Finalizações, No alvo, xG, Posse, Escanteios, Faltas, Amarelos, Vermelhos), the goals with minute, scorer and assister ("(contra)" for own goals, "(pên.)" for penalties), the cards, the substitutions and, if any, the shootout. Exit 3 for an unknown id. A match not yet played (`--date` earlier) prints "Ainda não disputado". |
| `season scorers [--limit N]` | Pos, player, club, goals, penalties, assists (default top 10) |
| `calibrate [--gate pr\|milestone] [--baseline PATH] [--write PATH] [--no-exploit]` | One line per target: metric, simulated value, target, band, verdict (OK / FORA / AVISO), source. Then the caution check, versions and the model hash. It exits 1 if any primary target is outside its band. `--write` saves the JSON report, and `--baseline` adds a "antes" column. The PR gate also runs the tactical exploit check (spec 006) and prints its line; `--no-exploit` skips it (faster, for checks that do not need it). |

`season fixtures`, `season day` and `season bracket` add the match id to each line (needed to
open `season match`), and lose "(provisório)" for quick-sim results.
