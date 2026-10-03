# Contract: Facade additions (004)

Added to `manager_core.api`. Views are immutable snapshots.

```python
def new_career(dataset: Dataset, name: str, club_id: str, master_seed: int | None = None,
               ruleset_id: str = DEFAULT_RULESET, year: int = 2027) -> Career
def load_career(saves: Path, name: str) -> Career            # raises SaveError(code)
def save_career(career: Career, saves: Path, name: str | None = None) -> Path
def list_saves(saves: Path) -> list[SaveSummary]
def delete_save(saves: Path, name: str) -> None
def continue_career(career: Career, saves: Path, *, to_season_end: bool = False) -> Stop
def career_status(career: Career) -> CareerStatus
def career_history(career: Career) -> list[SeasonRecord]
def suspended_players(career: Career, club_id: str) -> list[SuspensionView]
```

`Career.season` is a 002 `Season`, so every 002 and 003 view function works on it unchanged.
