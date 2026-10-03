"""Owner decisions 2026-10-03: booked-player caution depends on temperament and decisions, and a
goalkeeper takes in-play penalties only as a specialist."""

import random
from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.positions import Position
from manager_core.quicksim.engine import _Match, caution_strength, penalty_taker
from manager_core.quicksim.params import load_params
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import HOME
from tests.helpers import attrs, player

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


def _mind(temperament: int, decisions: int) -> object:
    return player(f"p-m{temperament}x{decisions}", positions={Position.DC: 20},
                  attributes=attrs(10, temperament=temperament, decisions=decisions))


# ---- caution strength -----------------------------------------------------------------


def test_strength_follows_temperament_and_decisions() -> None:
    params = load_params()
    low, high = int(params.caution.attribute_low), int(params.caution.attribute_high)
    assert caution_strength(_mind(low, low), params) == 0.0  # hot-head: no easing off
    assert caution_strength(_mind(high, high), params) == 1.0  # calm and smart: full effect
    mid = caution_strength(_mind(10, 10), params)
    assert 0.0 < mid < 1.0
    assert caution_strength(_mind(18, 10), params) > mid  # temperament counts
    assert caution_strength(_mind(10, 18), params) > mid  # decisions count


def test_strength_is_zero_when_the_behaviour_is_off() -> None:
    params = load_params().with_values(**{"caution.enabled": False})
    assert caution_strength(_mind(20, 20), params) == 0.0


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset)


def test_only_players_who_ease_off_pay_the_defensive_cost(provider: QuickSimProvider) -> None:
    sheet = provider.team_sheet("vale-do-ouro")
    match = _Match(sheet, provider.team_sheet("serra-negra"), provider.dataset.players,
                   provider.params, random.Random(1), neutral=False)
    side = match.sides[HOME]
    defenders = [pid for i, pid in sheet.starters if sheet.slot_position(i) is Position.DC]
    strengths = {pid: caution_strength(provider.dataset.player(pid), provider.params)
                 for pid in defenders}
    before = side.ratings.defence
    calm = max(defenders, key=lambda pid: strengths[pid])
    side.yellows[calm] = 1
    side.refresh(provider.params)
    drop = before - side.ratings.defence
    if strengths[calm] > 0:
        assert drop > 0
    # a booked hot-head (strength 0) costs nothing
    params = provider.params.with_values(**{"caution.attribute_low": 21.0,
                                            "caution.attribute_high": 22.0})
    side.refresh(params)
    assert side.ratings.defence == pytest.approx(before)


# ---- specialist goalkeepers ---------------------------------------------------------------


def _taker(pid: str, pen: int, position: Position = Position.ST) -> object:
    return player(f"p-{pid}", positions={position: 20}, attributes=attrs(10, penalty_taking=pen))


def test_keeper_never_takes_one_unless_a_specialist() -> None:
    params = load_params()
    threshold = params.penalties.keeper_specialist
    outfield = [_taker("a", 14), _taker("b", 12)]
    keeper = _taker("gk", threshold - 1, Position.GK)
    assert penalty_taker(outfield, keeper, params).id == "p-a"  # better than all, but no specialist


def test_specialist_keeper_takes_it_when_clearly_the_best() -> None:
    params = load_params()
    threshold = params.penalties.keeper_specialist
    keeper = _taker("gk", threshold + 1, Position.GK)
    assert penalty_taker([_taker("a", threshold - 2)], keeper, params).id == "p-gk"
    # a specialist still defers to an even better outfield taker
    assert penalty_taker([_taker("a", threshold + 3)], keeper, params).id == "p-a"


def test_no_keeper_on_the_pitch() -> None:
    params = load_params()
    assert penalty_taker([_taker("a", 10)], None, params).id == "p-a"
