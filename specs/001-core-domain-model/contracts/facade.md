# Contract: Core Facade `manager_core.api` (001)

This is the thin facade that every UI uses (CLI now, the TUI in 005, the Godot API in 010).
It returns plain, immutable data objects (no UI formatting). Signatures are indicative. Names
and types are binding for 001.

```python
def load_dataset(path: Path) -> LoadResult
    # LoadResult: report (ValidationReport) and dataset (Dataset | None; None if report has errors)

def validate_dataset(path: Path) -> ValidationReport

def export_dataset(dataset: Dataset, path: Path) -> ExportSummary

def generate_sample(seed: int = 20261002) -> Dataset

def list_clubs(dataset: Dataset) -> list[ClubSummary]

def squad(dataset: Dataset, club_id: ClubId, sort: SquadSort = "position") -> list[SquadEntry]

def player_profile(dataset: Dataset, player_id: PlayerId, include_hidden: bool = False) -> PlayerProfile

def rank_for_position(dataset: Dataset, club_id: ClubId, position: Position) -> list[PositionRanking]

def suggest_lineup(dataset: Dataset, club_id: ClubId, formation: str = "4-4-2") -> Lineup

def list_formations() -> list[Formation]
```

Errors: `NotFoundError(kind, id)` for an unknown club, player or formation. Validation problems
never raise. They are returned in the `ValidationReport`.

Determinism: every list is returned in a documented, stable order (sort key, then id).

Session note: in 001, callers hold and pass the `Dataset` object (in-process, M0). Spec 004
(saves) and spec 010 (out-of-process API) will introduce a session/handle in its place.
