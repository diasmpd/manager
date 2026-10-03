"""Unavailable (suspended) players are left out of team sheets (spec 004, T004)."""

import random
from datetime import date
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.results import MatchContext, Result
from manager_core.competition.season import Match, Season
from manager_core.domain.dataset import Dataset
from manager_core.domain.positions import Position
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.squad import BENCH_SIZE
from manager_core.ratings.ability import is_goalkeeper
from manager_core.ratings.suitability import suitability_milli

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


def _best_player(provider: QuickSimProvider, club: str) -> str:
    sheet = provider.team_sheet(club)
    return sheet.starters[-1][1]


def test_unavailable_player_never_plays(world: Dataset) -> None:
    provider = QuickSimProvider(world)
    star = _best_player(provider, "alvorada")
    for n in range(30):
        ctx = MatchContext(1, "x", unavailable=frozenset({star}))
        result = provider.play("m", world.club("alvorada"), world.club("serra-negra"), ctx,
                               random.Random(n))
        assert result.report is not None
        lineup = result.report.home_lineup
        assert star not in {pid for _, pid in lineup.starters} | set(lineup.bench)


def test_sheets_are_cached_per_unavailable_set(world: Dataset) -> None:
    provider = QuickSimProvider(world)
    star = _best_player(provider, "alvorada")
    without = provider.team_sheet("alvorada", frozenset({star}))
    assert provider.team_sheet("alvorada", frozenset({star})) is without
    assert provider.team_sheet("alvorada") is not without
    assert provider.team_sheet("alvorada", frozenset()) is provider.team_sheet("alvorada")


class _Ban:
    """A hook that bans one player for the whole season."""

    def __init__(self, player_id: str) -> None:
        self.player_id = player_id
        self.recorded: list[str] = []

    def unavailable(self, match: Match) -> frozenset[str]:
        return frozenset({self.player_id})

    def record(self, match: Match, result: Result) -> None:
        self.recorded.append(match.id)


def test_season_passes_the_hook_to_every_match(world: Dataset) -> None:
    provider = QuickSimProvider(world)
    star = _best_player(provider, "alvorada")
    hook = _Ban(star)
    season = api.start_season(world, "mg-modulo-i-2026", 2027, 4, result_provider=provider)
    season.discipline = hook
    season.advance_to(date(2027, 12, 31))
    assert sorted(hook.recorded) == sorted(season.results)
    for match_id, result in season.results.items():
        report = result.report
        assert report is not None
        for side in ("home", "away"):
            lineup = report.lineup(side)
            assert star not in {pid for _, pid in lineup.starters} | set(lineup.bench), match_id


def test_without_a_hook_nobody_is_unavailable(world: Dataset) -> None:
    season = Season.start(world, api.load_ruleset("mg-modulo-i-2026"), 2027, 4)
    assert season.discipline is None


def test_suspended_starter_is_replaced_by_the_best_fit(world: Dataset) -> None:
    provider = QuickSimProvider(world)
    base = provider.team_sheet("alvorada")
    slot, star = base.starters[-1]
    repaired = provider.team_sheet("alvorada", frozenset({star}))
    assert dict(repaired.starters)[slot] != star
    others = {pid for i, pid in repaired.starters if i != slot}
    assert others == {pid for i, pid in base.starters if i != slot}  # only that slot changes
    position = base.slot_position(slot)
    candidates = [p for p in world.squad("alvorada") if p.id != star and p.id not in others]
    best = max(candidates, key=lambda p: (suitability_milli(p, position), p.id))
    assert dict(repaired.starters)[slot] == best.id
    assert star not in repaired.bench and len(repaired.bench) == BENCH_SIZE


def test_suspended_keeper_is_replaced_by_a_keeper(world: Dataset) -> None:
    provider = QuickSimProvider(world)
    base = provider.team_sheet("alvorada")
    gk_slot, keeper = next((i, p) for i, p in base.starters
                           if base.slot_position(i) is Position.GK)
    repaired = provider.team_sheet("alvorada", frozenset({keeper}))
    assert is_goalkeeper(world.player(dict(repaired.starters)[gk_slot]))
