# Contract: Facade additions (002)

These functions are added to `manager_core.api`. All views are immutable snapshots. `Season` is
the in-process handle that specs 004 and 010 will persist and expose.

```python
def list_rulesets() -> list[RulesetSummary]
def load_ruleset(ruleset_id: str) -> Ruleset                  # raises RulesetError(report)
def validate_ruleset(path: Path) -> RulesetReport

def start_season(dataset: Dataset, ruleset_id: str, year: int, master_seed: int,
                 participants: Sequence[str] | None = None) -> Season
    # participants default: clubs whose state matches the ruleset, sorted by id; count must match

def advance_to(season: Season, day: date) -> list[SeasonEvent]   # plays every day up to and including `day`
def season_groups(season: Season) -> list[GroupView]
def season_fixtures(season: Season, club_id: str | None = None,
                    round: int | None = None) -> list[MatchView]
def season_table(season: Season, group: str | None = None) -> list[TableRow]   # None = overall
def season_bracket(season: Season) -> list[TieView]
def season_day(season: Season, day: date) -> DayView
def season_calendar(season: Season, month: int | None = None) -> list[CalendarDay]
def season_outcomes(season: Season) -> Outcome | None          # None until the season is complete
```

**Result provider**: `ResultProvider` protocol with
`play(match: MatchView, home: Club, away: Club, context: MatchContext) -> Result`.
`start_season` uses `PlaceholderProvider` unless a provider is passed explicitly, through the
keyword-only argument `result_provider=`. That argument is the replacement point for spec 003.
