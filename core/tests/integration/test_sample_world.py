"""US1: the committed fictional sample world (FR-024..028)."""

from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.dataset import Dataset
from manager_core.domain.positions import Line
from manager_core.ratings.ability import best_position, is_goalkeeper

REAL_MINEIRO_CLUBS = [
    "Atlético", "Cruzeiro", "América", "Tombense", "Athletic", "Ipatinga", "Pouso Alegre",
    "Democrata", "Villa Nova", "URT", "Caldense", "Uberlândia", "Itabirito", "North", "Betim",
    "Patrocinense",
]


@pytest.fixture(scope="module")
def world() -> Dataset:
    sample = Path(__file__).resolve().parents[3] / "data" / "sample"
    result = api.load_dataset(sample)
    assert result.dataset is not None, [i.message for i in result.report.errors]
    assert not [i for i in result.report.warnings if i.code == "W001"]
    return result.dataset


def test_twelve_clubs_in_tiers(world: Dataset) -> None:
    reps = sorted(c.reputation for c in world.clubs.values())
    assert len(reps) == 12
    assert sum(13 <= r <= 15 for r in reps) == 3
    assert sum(9 <= r <= 11 for r in reps) == 5
    assert sum(6 <= r <= 8 for r in reps) == 4


def test_playable_squads(world: Dataset) -> None:
    for club in world.clubs.values():
        players = world.squad(club.id)
        assert 25 <= len(players) <= 30, club.id
        assert sum(is_goalkeeper(p) for p in players) >= 3, club.id
        for line in (Line.DEF, Line.MID, Line.ATT):
            naturals = [p for p in players if best_position(p).line is line]
            assert len(naturals) >= 2, (club.id, line)


def test_age_distribution(world: Dataset) -> None:
    ages = [p.age(world.reference_date) for p in world.players.values()]
    assert all(16 <= a <= 38 for a in ages)
    assert sum(18 <= a <= 34 for a in ages) / len(ages) >= 0.80


def test_provenance_is_fictional(world: Dataset) -> None:
    assert world.fictional is True
    assert world.tool == "manager_core.sample"
    assert world.tool_version
    assert world.seed == api.DEFAULT_SEED
    assert world.sources


def test_no_real_club_names(world: Dataset) -> None:
    for club in world.clubs.values():
        for real in REAL_MINEIRO_CLUBS:
            assert real.lower() not in club.name.lower(), club.name
            assert real.lower() not in club.short_name.lower(), club.short_name
