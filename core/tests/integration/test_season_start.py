"""US1: starting a Mineiro season on the sample world."""

from collections import Counter
from datetime import timedelta
from itertools import pairwise
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


def test_groups_and_fixtures(world: Dataset) -> None:
    season = api.start_season(world, "mg-modulo-i-2026", 2027, 20261002)
    groups = api.season_groups(season)
    assert {g.club_ids[0] for g in groups} == {"vale-do-ouro", "serra-negra", "alvorada"}
    matches = api.season_fixtures(season)
    assert len(matches) == 48
    assert len({m.id for m in matches}) == 48
    per_club = Counter(c for m in matches for c in (m.home_id, m.away_id))
    assert set(per_club.values()) == {8}
    for m in matches:
        assert m.venue == world.club(m.home_id).stadium_name
        assert m.result is None


@pytest.mark.parametrize("seed", range(200))
def test_rest_and_window_invariants(world: Dataset, seed: int) -> None:
    season = api.start_season(world, "mg-modulo-i-2026", 2027, seed)
    matches = api.season_fixtures(season)
    by_club: dict[str, list] = {}
    for m in matches:
        assert m.kickoff.date().month in (1, 2, 3)
        for c in (m.home_id, m.away_id):
            by_club.setdefault(c, []).append(m.kickoff)
    for times in by_club.values():
        ordered = sorted(times)
        assert all(b - a >= timedelta(hours=66) for a, b in pairwise(ordered))


def test_start_is_deterministic(world: Dataset) -> None:
    a = api.start_season(world, "mg-modulo-i-2026", 2027, 42)
    b = api.start_season(world, "mg-modulo-i-2026", 2027, 42)
    assert api.season_groups(a) == api.season_groups(b)
    assert api.season_fixtures(a) == api.season_fixtures(b)


def test_year_outside_validity_refused(world: Dataset) -> None:
    with pytest.raises(SeasonError) as err:
        api.start_season(world, "mg-modulo-i-2026", 2025, 1)
    assert err.value.code == "S001"


def test_wrong_participant_count_refused(world: Dataset) -> None:
    with pytest.raises(SeasonError) as err:
        api.start_season(world, "mg-modulo-i-2026", 2027, 1,
                         participants=sorted(world.clubs)[:10])
    assert err.value.code == "S002"
