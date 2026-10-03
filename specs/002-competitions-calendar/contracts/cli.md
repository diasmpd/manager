# Contract: CLI `season` commands (002)

The CLI has no saves until spec 004, so every command rebuilds the season deterministically
from `--ruleset`, `--year` and `--master-seed`, then replays it up to `--date`. Output is pt-BR.
Placeholder results are marked "(provisório)".

**Shared options**

| Option | Default |
|---|---|
| `--ruleset` | `mg-modulo-i-2026` (2026 regulation, valid from 2026) |
| `--year` | `2027` |
| `--master-seed` | `20261002` |
| `--date YYYY-MM-DD` | the end of the season for result views; the start for the draw and the fixture list |

The global `--data` option from 001 also applies.

**Exit codes**: 0 ok; 1 invalid ruleset or dataset; 2 usage; 3 not found (club, group,
ruleset, month).

| Command | Output |
|---|---|
| `season groups` | Groups A/B/C with their clubs, in draw order |
| `season fixtures [--club ID] [--round N]` | Matches with date, kick-off, venue and score if played (by matchday, or one club's season) |
| `season table [--group A] [--overall]` | A group table, or the overall classification: Pos, club, P, W, D, L, GF, GA, GD, Pts, zone, decided-by |
| `season bracket` | Knockout ties per track (Mineiro and Inconfidência) with legs, aggregates, penalties and winners |
| `season day` | Everything on `--date`: matches with results, and events |
| `season calendar [--month 1-12]` | Day-by-day list of matches, events and reserved windows for a month, or a month-by-month summary of the year |
| `season outcomes` | Champion, runner-up, Inconfidência winner, relegated clubs, final classification |
| `season rules [--validate PATH]` | Lists the bundled rulesets, or validates a ruleset file (R-codes) |
