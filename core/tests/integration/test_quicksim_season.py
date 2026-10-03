"""Seasons played with the quick sim (US1, SC-003, SC-007)."""

import random
from datetime import date
from itertools import pairwise
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.results import MatchContext
from manager_core.competition.season import Season
from manager_core.competition.seeds import sub_seed
from manager_core.domain.dataset import Dataset
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import check_invariants

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
RULESET = "mg-modulo-i-2026"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


def _played(world: Dataset, seed: int) -> Season:
    season = api.start_season(world, RULESET, 2027, seed)
    api.advance_to(season, date(2027, 12, 31))
    return season


def test_quick_sim_is_the_default(world: Dataset) -> None:
    season = _played(world, 20261002)
    assert isinstance(season.provider, QuickSimProvider)
    for match_id, result in season.results.items():
        assert result.source == "quick_sim" and result.report is not None
        assert check_invariants(result.report, result) == [], match_id


def _check_season(season: Season) -> None:
    out = season.outcome()
    assert out is not None
    assert len(out.main_entrants) == 4 and len(out.relegated) == 2
    assert out.champion in out.main_entrants
    # cards are present on every result, so no table is settled by lots for lack of them
    assert all(r.has_cards for r in season.results.values())
    for group in season.groups:
        rows = season.group_table(group.label)
        for upper, lower in pairwise(rows):
            if upper.decided_by == "draw":
                assert (upper.points, upper.won, upper.goal_difference, upper.goals_for) == (
                    lower.points, lower.won, lower.goal_difference, lower.goals_for)


@pytest.mark.parametrize("seed", range(50))
def test_seasons_complete(world: Dataset, seed: int) -> None:
    _check_season(_played(world, seed))


@pytest.mark.slow
@pytest.mark.milestone
@pytest.mark.parametrize("seed", range(50, 1000))
def test_seasons_complete_1000(world: Dataset, seed: int) -> None:
    _check_season(_played(world, seed))


def test_a_match_replayed_alone_is_identical(world: Dataset) -> None:
    season = _played(world, 77)
    provider = QuickSimProvider(world)
    for match in list(season.sorted_matches())[::7]:
        rng = random.Random(sub_seed(season.seed, f"match:{match.id}"))
        neutral = season._context(match).neutral
        alone = provider.play(match.id, world.club(match.home_id), world.club(match.away_id),
                              MatchContext(season.seed, match.stage_id, neutral), rng)
        in_season = season.results[match.id]
        assert alone.report == in_season.report
        assert (alone.home_goals, alone.away_goals) == (in_season.home_goals,
                                                        in_season.away_goals)


def test_replay_is_identical(world: Dataset) -> None:
    assert _played(world, 5).results == _played(world, 5).results
