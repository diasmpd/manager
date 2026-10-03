# Data Model: Career Save and Game Loop (004)

Builds on 001 (`Dataset`), 002 (`Season`, `Ruleset`, `MatchContext`) and 003 (`Result`,
`MatchReport`, `QuickSimProvider`).

## Changes to earlier objects

| Object | Change |
|---|---|
| `MatchContext` (002) | + `unavailable: frozenset[str] = frozenset()`: suspended player ids for both clubs |
| `Season` (002) | + an optional `discipline` hook. Before playing a match it passes the suspended players of both clubs in `MatchContext.unavailable`. With no hook, nobody is suspended. |
| `QuickSimProvider` (003) | Team sheets are cached per (club, unavailable set). Suspended players are removed from the squad before the sheet is built. |
| `sample.generator` (001) | Exposes `make_player(...)` and `make_club(...)`; `generate()` output is unchanged |

## Career

| Entity | Fields |
|---|---|
| Career | name, master_seed, user_club_id, current_date, last_autosave (date), world (`Dataset` at the start of the current season), season (`Season`), history (list of `SeasonRecord`), pending (`Stop` or none) |
| Stop | kind (`user_match` / `event` / `season_end`), date, match_id (for `user_match`), events (`SeasonEvent`s of that day) |
| SeasonRecord | year, champion, runner_up, side_titles, relegated, promoted, final_classification, top_scorers (player, club, goals; top 10) |
| Discipline | per player: yellows (int), bans (int, matches still to serve); `suspended(club_id)` gives the ids for a club's next match |
| SeasonDefinition | ruleset_toml (text), year, season master seed, participants (sorted club ids) |

**State transitions**:

```
new --(start season)--> in_season
in_season --(continue: user match / event)--> in_season (stopped)
in_season --(season complete)--> season_end (stop)
season_end --(continue: rollover)--> in_season (next year)
```

## Save file (SQLite, format 1)

See [contracts/save-format.md](contracts/save-format.md).

**Invariants**:
- `load(save(c))` behaves like `c` for every later continue (SC-001).
- Discipline is never stored. It is rebuilt from the results.
- Results are never re-simulated on load. Stored results win.

## Reference data

| File | Content |
|---|---|
| `reference/career/development.toml` | age bands → mean ΔCA, standard deviation |
| `reference/career/retirement.toml` | age bands → base probability; form and personality factors |
| `reference/career/promoted-clubs.toml` | pool of fictional Minas towns (name, short name, abbreviation, colours, stadium) for promoted clubs |
