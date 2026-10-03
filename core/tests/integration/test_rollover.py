"""US4: the next season (spec 004 FR-011..FR-014, research R6-R9)."""

import statistics
from pathlib import Path

import pytest

from manager_core import api
from manager_core.career.career import SEASON_END, Career
from manager_core.career.rollover import next_season
from manager_core.domain.dataset import Dataset
from manager_core.ratings.ability import current_ability

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
SQUAD = 27


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


def _finish(career: Career, saves: Path) -> None:
    api.continue_career(career, saves, to_season_end=True)
    assert career.pending is not None and career.pending.kind == SEASON_END


def _squad(career: Career, club: str) -> list[str]:
    return [m.player_id for m in career.world.memberships.values() if m.club_id == club]


def test_rollover_rebuilds_the_league(world: Dataset, tmp_path: Path) -> None:
    career = api.new_career(world, "roll", "alvorada", master_seed=21)
    _finish(career, tmp_path)
    old = career.season
    outcome = old.outcome()
    assert outcome is not None
    before = {pid: current_ability(p) for pid, p in career.world.players.items()}
    old_ref = career.world.reference_date
    next_season(career)
    new = career.season
    assert new.year == old.year + 1
    assert len(new.participants) == 12
    assert not set(outcome.relegated) & set(new.participants)
    promoted = set(new.participants) - set(old.participants)
    assert len(promoted) == 2
    for club in new.participants:
        assert len(_squad(career, club)) == SQUAD, club
    assert career.world.reference_date.year == old_ref.year + 1
    record = career.history[-1]
    assert record.year == old.year and record.champion == outcome.champion
    assert set(record.relegated) == set(outcome.relegated)
    assert set(record.promoted) == promoted
    assert record.top_scorers and record.user_club == "alvorada"
    # development: young players grow on average, old ones decline
    young, old_players = [], []
    for pid, ca in before.items():
        if pid not in career.world.players:
            continue
        age = career.world.players[pid].age(career.world.reference_date)
        delta = current_ability(career.world.players[pid]) - ca
        if age <= 21:
            young.append(delta)
        elif age >= 34:
            old_players.append(delta)
    assert statistics.mean(young) > 0
    assert statistics.mean(old_players) < 0


def test_nobody_under_30_retires_and_youngsters_are_young(world: Dataset,
                                                          tmp_path: Path) -> None:
    career = api.new_career(world, "jovens", "alvorada", master_seed=22)
    _finish(career, tmp_path)
    ref = career.world.reference_date
    old_players = dict(career.world.players)
    next_season(career)
    new_ref = career.world.reference_date
    retired = set(old_players) - set(career.world.players)
    relegated_players = {pid for pid in retired if pid in old_players}
    for pid in relegated_players:
        assert old_players[pid].age(ref) + 1 >= 30 or pid not in old_players
    newcomers = set(career.world.players) - set(old_players)
    assert newcomers
    for pid in newcomers:
        age = career.world.players[pid].age(new_ref)
        promoted_club = career.world.memberships[pid].club_id not in {
            m.club_id for m in career.world.memberships.values() if m.player_id in old_players}
        assert promoted_club or 16 <= age <= 19, (pid, age)


def test_rollover_is_deterministic(world: Dataset, tmp_path: Path) -> None:
    a = api.new_career(world, "det", "serra-negra", master_seed=5)
    b = api.new_career(world, "det", "serra-negra", master_seed=5)
    for career, folder in ((a, "a"), (b, "b")):
        _finish(career, tmp_path / folder)
        next_season(career)
    assert a.world == b.world
    assert a.season.participants == b.season.participants
    assert a.history == b.history


def test_continue_after_season_end_rolls_over_and_saves(world: Dataset, tmp_path: Path) -> None:
    career = api.new_career(world, "seguinte", "alvorada", master_seed=3)
    _finish(career, tmp_path)
    year = career.season.year
    api.continue_career(career, tmp_path)
    assert career.season.year == year + 1
    loaded = api.load_career(tmp_path, "seguinte")
    assert loaded.season.year == year + 1 and loaded.history == career.history
    assert loaded.world == career.world


@pytest.mark.slow
def test_ten_seasons_stay_healthy(world: Dataset, tmp_path: Path) -> None:
    """SC-004 and SC-005 over a 10-season career."""
    career = api.new_career(world, "dez", "alvorada", master_seed=8)
    retirement_ages: list[int] = []
    for _ in range(10):
        _finish(career, tmp_path)
        before = dict(career.world.players)
        participants = set(career.season.participants)
        squads_before = {m.player_id for m in career.world.memberships.values()
                         if m.club_id in participants}
        next_season(career)
        gone = squads_before - set(career.world.players)
        # a player decides at the age he would have in the new season
        retirement_ages += [before[pid].age(career.world.reference_date) for pid in gone]
        assert len(career.season.participants) == 12
        ages = [career.world.players[m.player_id].age(career.world.reference_date)
                for m in career.world.memberships.values()
                if m.club_id in career.season.participants]
        assert 24 <= statistics.mean(ages) <= 28
        for club in career.season.participants:
            assert len(_squad(career, club)) == SQUAD
    assert retirement_ages and min(retirement_ages) >= 30
    assert 34 <= statistics.median(retirement_ages) <= 36
