# Data Model: Competitions and Calendar (002)

Builds on 001 (`Dataset`, `Club`, `Player`). Ruleset objects are immutable. `Season` is the
engine object holding mutable progress; every view it returns is an immutable snapshot.

## Ruleset (reference data, contracts/ruleset-format.md)

| Entity | Fields |
|---|---|
| Ruleset | id, name, short_name, state, country, regulation_year, valid_from, valid_to (optional), participants, scoring (win/draw/loss points), tiebreakers (ordered list of `Tiebreaker`), calendar (`CalendarRule`), venues (neutral venue or none), stages (ordered `StageRule`s) |
| CalendarRule | window_start (month-day), window_end (month-day), weekend_days, midweek_days, kickoff_weekend, kickoff_midweek, min_rest_hours, avoid_windows (labels) |
| StageRule (groups) | id, name (optional display name), type=`groups`, group_count, group_size, matching (`own_group` / `other_groups` / `all`), rounds (1 or 2), draw (`pots_by_reputation` / `fixed`), outcomes (list of `OutcomeRule`) |
| StageRule (knockout) | id, name (optional display name), type=`knockout`, track (`main` or a side-title id), title (only for the final stage of a track), legs (1 or 2), entrants (list of `EntrantRule`), pairing, deciding_leg_host, tie_rule, venue (`home` / `neutral`), dates_with (optional stage id whose slots it shares), may_exceed_window (bool, default false) |
| EntrantRule | source stage id, rule (`group_winners` / `best_of_place` place+count / `overall_places` from–to / `winners_of`), exclude_tracks (for `overall_places`: tracks whose entrants are skipped, next places fill in) |
| OutcomeRule | kind (`relegated`), source (`overall_places` from–to) |
| Tiebreaker (enum) | `wins`, `goal_difference`, `goals_for`, `head_to_head`, `fewer_red_cards`, `fewer_yellow_cards`, `draw` |

**Validation (`R` codes, all reported at once)**

| Code | Rule |
|---|---|
| R001 | file unreadable or not valid TOML |
| R002 | required key missing or wrong type |
| R003 | unknown enum value (stage type, matching, tiebreaker, pairing, tie rule, venue) |
| R004 | participants ≠ group_count × group_size |
| R005 | stage reference to an unknown or later stage |
| R006 | place out of range (e.g. `overall_places` 11–13 with 12 clubs) |
| R007 | knockout entrants not a power of two (not reported when an entrant rule was already rejected) |
| R008 | `venue = "neutral"` without a neutral venue declared |
| R009 | `head_to_head` with `draw` not last, or `draw` missing (no total order) |
| R010 | window_end before window_start, or min_rest_hours < 0 |
| R011 | `other_groups` matching with fewer than 2 groups |
| R012 | two tracks can take the same club (an `overall_places` entrant rule drawing from the same stage as another track's entrant rule without `exclude_tracks`; two `overall_places` rules with disjoint ranges do not overlap) |
| R013 | invalid validity range (`valid_to` < `valid_from`, or missing `valid_from`) |
| R014 | kick-off defaults and `min_rest_hours` make a weekend match after a midweek match impossible |

**Season start errors**: `S001` season year outside the ruleset's validity range; `S002` wrong
number of participants; `S003` the window cannot fit the rounds (`SchedulingError`).

## Season (engine)

| Entity | Fields |
|---|---|
| Season | ruleset, year, season_seed, participants (club ids, sorted), current_date, stages (`StageState`), matches (by id), events (ordered `SeasonEvent`), outcomes (`Outcome` once known), result_provider |
| Group | label (A, B, C…), club ids (draw order) |
| Match | id (`{stage}-{round}-{n}`, stable), stage_id, round (matchday or leg number), home_id, away_id, date, kickoff (time), venue_name, result (`Result` or none), tie_id (knockout ties) |
| Result | home_goals, away_goals, source (`placeholder` / later `quick_sim` / `engine`), red/yellow cards per side (optional), shootout (`Shootout` or none) |
| Shootout | kicks: ordered list of (club_id, scored), winner_id |
| KnockoutTie | id, stage_id, club ids (higher campaign first), matches (1 or 2), winner_id (once decided), decided_by (`aggregate` / `penalties` / `points` / `campaign`) |
| TableRow | club_id, played, won, drawn, lost, goals_for, goals_against, goal_difference, points, red_cards?, yellow_cards?, place, decided_by (criterion that separated it from the next row), zone (`track:<track>` for the entrants of a track's first knockout stage, `relegated`, or none; the display text comes from the ruleset's stage names and track titles) |
| SeasonEvent | date, kind (`draw`, `stage_complete`, `qualified`, `paired`, `relegated`, `champion`, `side_champion`), payload |
| Outcome | champion, runner_up, main_entrants (entrants of the main track's first knockout stage), side titles (track → winner), relegated (list), final classification (list of club ids) |
| SeasonCalendar | year, days (date → `CalendarDay`) |
| CalendarDay | date, match_ids, events, windows (`ReservedWindow`s), reserved_stages (knockout stages whose dates are held but not yet paired) |
| ReservedWindow | label, name, start, end, blocks (e.g. `state`). Sources: fixed month-day ranges; a per-year file whose windows replace the fixed ones with the same label; Easter offsets |

**State transitions** (driven by `advance_to(date)`):

```
created --(start: draw + fixtures + dates for group stage)--> group_stage
group_stage --(last group-stage match played)--> qualification decided
  -> knockout ties paired and dated (main + side tracks); relegation outcome recorded
knockout round n --(all ties decided)--> round n+1 paired/dated, or track finished
all tracks finished --> completed (Outcome final)
```

Invariants checked in tests:
- every club plays exactly once per group-stage matchday;
- no club plays twice within `min_rest_hours`;
- match ids are stable for a given seed;
- results never change once played (a replay is identical).
