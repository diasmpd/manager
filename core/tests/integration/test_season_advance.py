"""US2: advancing the season day by day."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.season import SeasonError
from manager_core.domain.dataset import Dataset

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    dataset = api.load_dataset(SAMPLE).dataset
    assert dataset is not None
    return dataset


def test_day_without_matches_only_moves_date(world: Dataset) -> None:
    season = api.start_season(world, "mg-modulo-i-2026", 2027, 5)
    events = api.advance_to(season, date(2027, 1, 5))
    assert season.current_date == date(2027, 1, 5)
    assert not season.results
    assert all(e.kind == "draw" for e in events)


def test_first_matchday_updates_tables(world: Dataset) -> None:
    season = api.start_season(world, "mg-modulo-i-2026", 2027, 5)
    api.advance_to(season, date(2027, 1, 10))
    assert len(season.results) == 6
    assert sum(r.played for r in api.season_table(season)) == 12


def test_daily_steps_equal_one_jump(world: Dataset) -> None:
    a = api.start_season(world, "mg-modulo-i-2026", 2027, 9)
    b = api.start_season(world, "mg-modulo-i-2026", 2027, 9)
    day = date(2027, 1, 1)
    while day < date(2027, 4, 1):
        day += timedelta(days=1)
        api.advance_to(a, day)
    api.advance_to(b, date(2027, 4, 1))
    assert api.season_outcomes(a) == api.season_outcomes(b)
    assert [e for e in a.events] == [e for e in b.events]


def test_cannot_go_past_year_end(world: Dataset) -> None:
    season = api.start_season(world, "mg-modulo-i-2026", 2027, 1)
    with pytest.raises(SeasonError) as err:
        api.advance_to(season, date(2028, 1, 1))
    assert err.value.code == "S004"


def test_events_in_date_order(world: Dataset) -> None:
    season = api.start_season(world, "mg-modulo-i-2026", 2027, 2)
    api.advance_to(season, date(2027, 12, 31))
    days = [e.day for e in season.events]
    assert days == sorted(days)
    kinds = [e.kind for e in season.events]
    for kind in ("draw", "stage_complete", "qualified", "relegated", "paired", "champion", "title"):
        assert kind in kinds
    assert kinds.index("draw") < kinds.index("relegated") < kinds.index("champion")
