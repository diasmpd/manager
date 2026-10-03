"""Player-based penalty shootouts (US4, FR-013, research R11)."""

import random
from datetime import date
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.results import MatchContext
from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.quicksim.engine import kick_factor, penalty_order, simulate_match
from manager_core.quicksim.params import load_params
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import keeper_at_end
from manager_core.quicksim.shootout import kick_takers, play_shootout, shootout_orders
from tests.helpers import attrs, player

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


def _side(prefix: str, penalty: int = 12, keeper_skill: int = 12) -> tuple[list[Player], Player]:
    outfield = [player(f"{prefix}{i:02d}", positions={Position.MC: 20},
                       attributes=attrs(12, penalty_taking=penalty + (i % 3), composure=12))
                for i in range(10)]
    keeper = player(f"{prefix}gk", positions={Position.GK: 20},
                    attributes=attrs(12, reflexes=keeper_skill, agility=keeper_skill,
                                     one_on_ones=keeper_skill, anticipation=keeper_skill))
    return [*outfield, keeper], keeper


def test_rules_and_order() -> None:
    params = load_params()
    a, a_gk = _side("a")
    b, b_gk = _side("b")
    for n in range(300):
        shootout = play_shootout("A", a, a_gk, "B", b, b_gk, params, random.Random(n))
        clubs = [c for c, _ in shootout.kicks]
        assert clubs[::2] == ["A"] * len(clubs[::2]) and clubs[1::2] == ["B"] * len(clubs[1::2])
        assert len(shootout.kicks) >= 6  # at least 3 kicks each before anyone can win
        takers = kick_takers(shootout, a, a_gk, b, b_gk)
        a_takers = takers[::2]
        outfield = [p for p in a if p is not a_gk]
        best = sorted(outfield, key=lambda p: (-p.attributes.get("penalty_taking"),
                                               -p.attributes.get("composure"), p.id))
        best.append(a_gk)  # the keeper kicks last
        assert a_takers == [best[i % len(best)].id for i in range(len(a_takers))]


def test_conversion_is_near_the_real_rate() -> None:
    params = load_params()
    a, a_gk = _side("a")
    b, b_gk = _side("b")
    kicks = scored = 0
    for n in range(4000):
        shootout = play_shootout("A", a, a_gk, "B", b, b_gk, params, random.Random(f"c{n}"))
        kicks += len(shootout.kicks)
        scored += sum(s for _, s in shootout.kicks)
    assert 0.65 <= scored / kicks <= 0.85


def test_takers_and_keepers_matter() -> None:
    params = load_params()
    good, _ = _side("g", penalty=18)
    poor, _ = _side("p", penalty=6)
    _, average_keeper = _side("k")
    _, great_keeper = _side("x", keeper_skill=19)
    assert kick_factor(params, good[0], average_keeper) > kick_factor(params, poor[0],
                                                                      average_keeper)
    assert kick_factor(params, good[0], great_keeper) < kick_factor(params, good[0],
                                                                    average_keeper)


def test_only_finishers_kick() -> None:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    provider = QuickSimProvider(loaded.dataset)
    home, away = loaded.dataset.club("alvorada"), loaded.dataset.club("serra-negra")
    for n in range(40):
        result, report = simulate_match(provider.team_sheet(home.id),
                                        provider.team_sheet(away.id),
                                        loaded.dataset.players, provider.params,
                                        random.Random(f"so:{n}"))
        shootout = provider.shootout("m", home, away, MatchContext(1, "final"),
                                     random.Random(n), last_result=result)
        first = [loaded.dataset.player(p) for p in sorted(report.home_finishers)]
        second = [loaded.dataset.player(p) for p in sorted(report.away_finishers)]
        keepers = [keeper_at_end(report, side) for side in ("home", "away")]
        takers = kick_takers(shootout, first,
                             loaded.dataset.player(keepers[0]) if keepers[0] else None,
                             second, loaded.dataset.player(keepers[1]) if keepers[1] else None)
        allowed = set(report.home_finishers) | set(report.away_finishers)
        assert set(takers) <= allowed
    # without a report it still works, from the starting XI
    shootout = provider.shootout("m", home, away, MatchContext(1, "final"), random.Random(1))
    assert shootout.winner_id in (home.id, away.id)


@pytest.mark.parametrize("seed", range(3))
def test_season_shootouts_are_valid(seed: int) -> None:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    season = api.start_season(loaded.dataset, "mg-modulo-i-2026", 2027, seed)

    api.advance_to(season, date(2027, 12, 31))
    for result in season.results.values():
        if result.shootout is not None:
            assert result.report is not None
            assert result.shootout.winner_id in {k[0] for k in result.shootout.kicks}


def test_larger_side_reduces_to_equate() -> None:
    """IFAB Law 10: a team with more players reduces to the opponents' number before the kicks.
    It leaves out its worst takers and keeps its goalkeeper."""
    params = load_params()
    a, a_gk = _side("a")  # 11 players
    b, b_gk = _side("b")
    b = [p for p in b if p.id != "b00"]  # 10 players: one was sent off
    worst_a = penalty_order([p for p in a if p is not a_gk])[-1]
    orders = shootout_orders(a, a_gk, b, b_gk)
    assert len(orders[0]) == len(orders[1]) == 10
    assert a_gk in orders[0] and orders[0][-1] is a_gk
    assert worst_a not in orders[0]
    for n in range(200):
        shootout = play_shootout("A", a, a_gk, "B", b, b_gk, params, random.Random(f"eq{n}"))
        takers = kick_takers(shootout, a, a_gk, b, b_gk)
        assert worst_a.id not in takers[::2]
        a_takers = takers[::2]
        assert a_takers == [orders[0][i % 10].id for i in range(len(a_takers))]


def test_equal_sides_are_not_reduced() -> None:
    a, a_gk = _side("a")
    b, b_gk = _side("b")
    first, second = shootout_orders(a, a_gk, b, b_gk)
    assert len(first) == len(second) == 11
