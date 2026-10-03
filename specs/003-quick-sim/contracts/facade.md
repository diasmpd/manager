# Contract: Facade additions (003)

Added to `manager_core.api`. All return immutable snapshots.

```python
def match_report(season: Season, match_id: str) -> MatchReportView
    # raises NotFoundError("match") for an unknown id; MatchReportView.report is None until played

def season_scorers(season: Season, limit: int | None = None) -> list[ScorerRow]
    # ScorerRow(player_id, player_name, club_id, club_name, goals, penalties, assists)
    # ordered by goals desc, then assists desc, then fewer penalties, then player id

def run_calibration(dataset: Dataset, gate: str = "pr",
                    baseline: Path | None = None) -> CalibrationReport
    # gate: "pr" | "milestone"; deterministic; never writes files (the CLI does)
```

**Changed in 002's facade**: `start_season(..., *, result_provider=None)` now defaults to
`QuickSimProvider(dataset)`. Passing `PlaceholderProvider(dataset)` keeps 002's behaviour.

**Provider protocol** (`competition.results`):

```python
class ResultProvider(Protocol):
    def play(self, match_id: str, home: Club, away: Club, context: MatchContext,
             rng: random.Random) -> Result: ...
    def shootout(self, match_id: str, first: Club, second: Club, context: MatchContext,
                 rng: random.Random, *, last_result: Result | None = None) -> Shootout: ...
```

`QuickSimProvider(dataset, params: ModelParams | None = None)` loads the bundled
`model.toml` when `params` is None. The harness and the tuning tool pass explicit parameters.
